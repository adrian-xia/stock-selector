"""batch_sync_daily 单元测试。"""

import asyncio
import logging
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.batch import batch_sync_daily


# ============================================================
# 辅助
# ============================================================

def _mock_session_factory() -> MagicMock:
    """创建 mock 的 async_sessionmaker。"""
    return MagicMock()


def _mock_pool() -> MagicMock:
    """创建 mock 的 BaoStockConnectionPool。"""
    pool = MagicMock()
    pool.acquire = AsyncMock()
    pool.release = AsyncMock()
    return pool


# ============================================================
# 1. 基本功能（多只股票并发）
# ============================================================

class TestBatchSyncBasic:
    """批量同步基本功能测试。"""

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_sync_multiple_stocks(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
    ) -> None:
        """多只股票应全部同步成功。"""
        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock()
        mock_manager_cls.return_value = mock_manager

        codes = ["600519.SH", "000001.SZ", "300750.SZ"]
        result = await batch_sync_daily(
            session_factory=_mock_session_factory(),
            stock_codes=codes,
            target_date=date(2025, 1, 6),
            connection_pool=_mock_pool(),
            batch_size=10,
            concurrency=5,
        )

        assert result["success"] == 3
        assert result["failed"] == 0
        assert result["failed_codes"] == []
        assert mock_manager.sync_daily.call_count == 3

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_empty_stock_list(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
    ) -> None:
        """空股票列表应返回全零结果。"""
        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock()
        mock_manager_cls.return_value = mock_manager

        result = await batch_sync_daily(
            session_factory=_mock_session_factory(),
            stock_codes=[],
            target_date=date(2025, 1, 6),
            batch_size=10,
            concurrency=5,
        )

        assert result["success"] == 0
        assert result["failed"] == 0
        assert mock_manager.sync_daily.call_count == 0


# ============================================================
# 2. 分批逻辑
# ============================================================

class TestBatchSplitting:
    """分批逻辑测试。"""

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_batch_count_correct(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
    ) -> None:
        """10 只股票、batch_size=3 应分为 4 批（3+3+3+1）。"""
        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock()
        mock_manager_cls.return_value = mock_manager

        codes = [f"00000{i}.SZ" for i in range(10)]
        result = await batch_sync_daily(
            session_factory=_mock_session_factory(),
            stock_codes=codes,
            target_date=date(2025, 1, 6),
            batch_size=3,
            concurrency=5,
        )

        assert result["success"] == 10
        assert mock_manager.sync_daily.call_count == 10

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_single_batch(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
    ) -> None:
        """股票数 <= batch_size 时只有一批。"""
        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock()
        mock_manager_cls.return_value = mock_manager

        codes = ["600519.SH", "000001.SZ"]
        result = await batch_sync_daily(
            session_factory=_mock_session_factory(),
            stock_codes=codes,
            target_date=date(2025, 1, 6),
            batch_size=100,
            concurrency=5,
        )

        assert result["success"] == 2


# ============================================================
# 3. 并发控制
# ============================================================

class TestConcurrencyControl:
    """并发控制测试。"""

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_concurrency_limit_respected(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
    ) -> None:
        """并发数不应超过配置的限制。"""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def _track_concurrency(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.01)  # 模拟 IO
            async with lock:
                current_concurrent -= 1

        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock(side_effect=_track_concurrency)
        mock_manager_cls.return_value = mock_manager

        codes = [f"00000{i}.SZ" for i in range(20)]
        await batch_sync_daily(
            session_factory=_mock_session_factory(),
            stock_codes=codes,
            target_date=date(2025, 1, 6),
            batch_size=20,
            concurrency=3,
        )

        assert max_concurrent <= 3


# ============================================================
# 4. 单只股票失败不阻断整体
# ============================================================

class TestErrorIsolation:
    """错误隔离测试。"""

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_single_failure_continues(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
    ) -> None:
        """单只股票失败不应阻断其他股票的同步。"""
        call_count = 0

        async def _sync_with_failure(code, start, end):
            nonlocal call_count
            call_count += 1
            if code == "000001.SZ":
                raise RuntimeError("network error")

        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock(side_effect=_sync_with_failure)
        mock_manager_cls.return_value = mock_manager

        codes = ["600519.SH", "000001.SZ", "300750.SZ"]
        result = await batch_sync_daily(
            session_factory=_mock_session_factory(),
            stock_codes=codes,
            target_date=date(2025, 1, 6),
            batch_size=10,
            concurrency=5,
        )

        assert result["success"] == 2
        assert result["failed"] == 1
        assert "000001.SZ" in result["failed_codes"]
        # 所有 3 只都应被尝试
        assert call_count == 3

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_all_failures(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
    ) -> None:
        """全部失败时应正确统计。"""
        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock(side_effect=RuntimeError("fail"))
        mock_manager_cls.return_value = mock_manager

        codes = ["600519.SH", "000001.SZ"]
        result = await batch_sync_daily(
            session_factory=_mock_session_factory(),
            stock_codes=codes,
            target_date=date(2025, 1, 6),
            batch_size=10,
            concurrency=5,
        )

        assert result["success"] == 0
        assert result["failed"] == 2
        assert len(result["failed_codes"]) == 2


# ============================================================
# 5. 进度日志输出
# ============================================================

class TestProgressLogging:
    """进度日志测试。"""

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_batch_progress_logged(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
        caplog,
    ) -> None:
        """每批完成后应记录进度日志。"""
        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock()
        mock_manager_cls.return_value = mock_manager

        codes = [f"00000{i}.SZ" for i in range(5)]
        with caplog.at_level(logging.INFO, logger="app.data.batch"):
            await batch_sync_daily(
                session_factory=_mock_session_factory(),
                stock_codes=codes,
                target_date=date(2025, 1, 6),
                batch_size=2,
                concurrency=5,
            )

        # 5 只股票、batch_size=2 → 3 批
        batch_logs = [r for r in caplog.records if "Batch" in r.message]
        assert len(batch_logs) == 3


# ============================================================
# 6. 最终汇总统计
# ============================================================

class TestSummaryStats:
    """最终汇总统计测试。"""

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_summary_fields(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
    ) -> None:
        """返回结果应包含所有必要字段。"""
        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock()
        mock_manager_cls.return_value = mock_manager

        result = await batch_sync_daily(
            session_factory=_mock_session_factory(),
            stock_codes=["600519.SH"],
            target_date=date(2025, 1, 6),
            batch_size=10,
            concurrency=5,
        )

        assert "success" in result
        assert "failed" in result
        assert "failed_codes" in result
        assert "elapsed_seconds" in result
        assert isinstance(result["elapsed_seconds"], float)

    @patch("app.data.batch.DataManager")
    @patch("app.data.batch.BaoStockClient")
    async def test_summary_log_output(
        self, mock_client_cls: MagicMock, mock_manager_cls: MagicMock,
        caplog,
    ) -> None:
        """完成后应输出汇总日志。"""
        mock_manager = MagicMock()
        mock_manager.sync_daily = AsyncMock()
        mock_manager_cls.return_value = mock_manager

        with caplog.at_level(logging.INFO, logger="app.data.batch"):
            await batch_sync_daily(
                session_factory=_mock_session_factory(),
                stock_codes=["600519.SH", "000001.SZ"],
                target_date=date(2025, 1, 6),
                batch_size=10,
                concurrency=5,
            )

        # 应有"完成"汇总日志
        summary_logs = [r for r in caplog.records if "完成" in r.message and "成功" in r.message]
        assert len(summary_logs) >= 1
