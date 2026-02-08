"""日线同步性能集成测试。

这些测试需要：
1. 运行中的 PostgreSQL 实例
2. 运行中的 Redis 实例（可选）
3. BaoStock API 可访问

运行方式：
    # 设置环境变量指向测试数据库
    export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test_db"

    # 运行集成测试
    pytest tests/integration/test_daily_sync_performance.py -v -s
"""

import asyncio
import time
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.batch import batch_sync_daily
from app.data.pool import BaoStockConnectionPool, close_pool, get_pool
from app.database import async_session_factory
from app.scheduler.jobs import sync_daily_step

# 默认跳过集成测试，除非显式启用
pytestmark = pytest.mark.skipif(
    True,  # 改为 False 以启用集成测试
    reason="需要真实数据库和 BaoStock API，默认跳过",
)


# ============================================================
# 1. 完整批量同步流程
# ============================================================

class TestBatchSyncIntegration:
    """批量同步集成测试（使用真实数据库）。"""

    @pytest.mark.asyncio
    async def test_batch_sync_with_real_db(self) -> None:
        """测试批量同步写入真实数据库。

        注意：此测试需要真实数据库和 BaoStock API。
        """
        # 创建连接池
        pool = get_pool()

        # 选择少量股票进行测试
        test_codes = ["600519.SH", "000001.SZ"]
        target_date = date(2025, 1, 6)

        try:
            result = await batch_sync_daily(
                session_factory=async_session_factory,
                stock_codes=test_codes,
                target_date=target_date,
                connection_pool=pool,
                batch_size=10,
                concurrency=2,
            )

            # 验证结果
            assert result["success"] + result["failed"] == len(test_codes)
            assert "elapsed_seconds" in result

            # TODO: 查询数据库验证数据已写入

        finally:
            await close_pool()

    @pytest.mark.asyncio
    async def test_batch_sync_performance_baseline(self) -> None:
        """测试批量同步性能基准。

        对比串行同步和批量同步的耗时差异。
        """
        # TODO: 实现性能对比测试
        pass


# ============================================================
# 2. 调度器集成
# ============================================================

class TestSchedulerIntegration:
    """调度器使用批量同步的集成测试。"""

    @pytest.mark.asyncio
    async def test_sync_daily_step_uses_batch(self) -> None:
        """测试 sync_daily_step 使用批量同步。"""
        # Mock DataManager.get_stock_list 返回少量股票
        with patch("app.scheduler.jobs.DataManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.get_stock_list = AsyncMock(return_value=[
                {"ts_code": "600519.SH"},
                {"ts_code": "000001.SZ"},
            ])
            mock_manager.is_trade_day = AsyncMock(return_value=True)
            mock_manager_cls.return_value = mock_manager

            # Mock batch_sync_daily
            with patch("app.scheduler.jobs.batch_sync_daily") as mock_batch:
                mock_batch.return_value = {
                    "success": 2,
                    "failed": 0,
                    "failed_codes": [],
                    "elapsed_seconds": 1.5,
                }

                await sync_daily_step(date(2025, 1, 6))

                # 验证 batch_sync_daily 被调用
                mock_batch.assert_called_once()
                call_kwargs = mock_batch.call_args.kwargs
                assert len(call_kwargs["stock_codes"]) == 2
                assert call_kwargs["connection_pool"] is not None


# ============================================================
# 3. 性能验证
# ============================================================

class TestPerformanceImprovement:
    """性能提升验证测试。"""

    @pytest.mark.asyncio
    async def test_measure_sync_time(self) -> None:
        """测量批量同步耗时。

        记录同步 N 只股票的实际耗时，用于性能分析。
        """
        pool = get_pool()
        test_codes = [f"00000{i}.SZ" for i in range(10)]

        start = time.monotonic()
        try:
            result = await batch_sync_daily(
                session_factory=async_session_factory,
                stock_codes=test_codes,
                target_date=date(2025, 1, 6),
                connection_pool=pool,
                batch_size=5,
                concurrency=3,
            )
            elapsed = time.monotonic() - start

            print(f"\n同步 {len(test_codes)} 只股票耗时: {elapsed:.2f}s")
            print(f"成功: {result['success']}, 失败: {result['failed']}")

        finally:
            await close_pool()


# ============================================================
# 4. 连接池生命周期
# ============================================================

class TestConnectionPoolLifecycle:
    """连接池在调度器中的生命周期测试。"""

    @pytest.mark.asyncio
    async def test_pool_initialization(self) -> None:
        """测试连接池初始化。"""
        pool = get_pool()
        assert pool is not None
        assert await pool.health_check() is True
        await close_pool()

    @pytest.mark.asyncio
    async def test_pool_reuse_across_calls(self) -> None:
        """测试连接池在多次调用间复用。"""
        pool1 = get_pool()
        pool2 = get_pool()
        assert pool1 is pool2  # 应该是同一个实例
        await close_pool()

    @pytest.mark.asyncio
    async def test_pool_cleanup_on_close(self) -> None:
        """测试连接池关闭时正确清理。"""
        pool = get_pool()
        await close_pool()
        assert await pool.health_check() is False
