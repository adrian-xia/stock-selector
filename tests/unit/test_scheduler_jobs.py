"""测试调度器任务逻辑。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler.jobs import run_post_market_chain, retry_failed_stocks_job


# 所有调用 run_post_market_chain 的测试都需要 mock _task_logger（避免真实数据库写入）
_mock_task_logger = patch("app.scheduler.jobs._task_logger", new_callable=AsyncMock)


class TestRunPostMarketChain:
    """测试盘后链路。"""

    @_mock_task_logger
    @patch("app.scheduler.jobs._build_manager")
    async def test_skip_non_trading_day(
        self, mock_build: MagicMock, mock_tl: AsyncMock
    ) -> None:
        """非交易日应跳过整个链路。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = False
        mock_build.return_value = mock_mgr

        await run_post_market_chain(date(2024, 1, 6))  # 周六

        mock_mgr.is_trade_day.assert_called_once_with(date(2024, 1, 6))
        # 不应获取同步锁
        mock_mgr.acquire_sync_lock.assert_not_called()

    @_mock_task_logger
    @patch("app.scheduler.jobs.pipeline_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs.cache_refresh_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs._build_manager")
    async def test_full_chain_on_trading_day(
        self,
        mock_build: MagicMock,
        mock_cache: AsyncMock,
        mock_pipeline: AsyncMock,
        mock_tl: AsyncMock,
    ) -> None:
        """交易日应按顺序执行全部步骤（含完整性门控通过）。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = True
        mock_mgr.acquire_sync_lock.return_value = True
        mock_mgr.sync_stock_list.return_value = {"inserted": 0, "updated": 0}
        mock_mgr.reset_stale_status.return_value = 0
        mock_mgr.init_sync_progress.return_value = {"inserted": 0}
        mock_mgr.sync_delisted_status.return_value = {"updated": 0}
        mock_mgr.get_stocks_needing_sync.return_value = ["600519.SH"]
        mock_mgr.get_sync_summary.return_value = {
            "total": 100, "data_done": 98, "indicator_done": 98,
            "failed": 0, "completion_rate": 0.98,
        }
        mock_build.return_value = mock_mgr

        target = date(2024, 1, 8)
        await run_post_market_chain(target)

        mock_mgr.acquire_sync_lock.assert_called_once()
        mock_mgr.reset_stale_status.assert_called_once()
        mock_mgr.init_sync_progress.assert_called_once()
        mock_mgr.sync_delisted_status.assert_called_once()
        mock_mgr.process_stocks_batch.assert_called_once()
        mock_pipeline.assert_called_once_with(target)
        mock_mgr.release_sync_lock.assert_called_once()

    @_mock_task_logger
    @patch("app.scheduler.jobs._build_manager")
    async def test_skip_when_lock_occupied(
        self, mock_build: MagicMock, mock_tl: AsyncMock
    ) -> None:
        """同步锁被占用时应跳过。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = True
        mock_mgr.acquire_sync_lock.return_value = False
        mock_build.return_value = mock_mgr

        await run_post_market_chain(date(2024, 1, 8))

        mock_mgr.acquire_sync_lock.assert_called_once()
        # 不应执行后续步骤
        mock_mgr.reset_stale_status.assert_not_called()

    @_mock_task_logger
    @patch("app.scheduler.jobs.pipeline_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs.cache_refresh_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs._build_manager")
    async def test_skip_strategy_when_below_threshold(
        self,
        mock_build: MagicMock,
        mock_cache: AsyncMock,
        mock_pipeline: AsyncMock,
        mock_tl: AsyncMock,
    ) -> None:
        """完成率低于阈值时应跳过策略执行。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = True
        mock_mgr.acquire_sync_lock.return_value = True
        mock_mgr.sync_stock_list.return_value = {"inserted": 0, "updated": 0}
        mock_mgr.reset_stale_status.return_value = 0
        mock_mgr.init_sync_progress.return_value = {"inserted": 0}
        mock_mgr.sync_delisted_status.return_value = {"updated": 0}
        mock_mgr.get_stocks_needing_sync.return_value = []
        mock_mgr.get_sync_summary.return_value = {
            "total": 100, "data_done": 80, "indicator_done": 80,
            "failed": 20, "completion_rate": 0.80,
        }
        mock_build.return_value = mock_mgr

        await run_post_market_chain(date(2024, 1, 8))

        # 策略不应执行
        mock_pipeline.assert_not_called()
        mock_mgr.release_sync_lock.assert_called_once()
