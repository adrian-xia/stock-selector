"""测试定时重试逻辑（Task 10.5）。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler.jobs import retry_failed_stocks_job


class TestRetryFailedStocksJob:
    """测试 retry_failed_stocks_job()。"""

    @patch("app.scheduler.jobs._build_manager")
    async def test_skip_when_lock_occupied(self, mock_build) -> None:
        """锁被占用时跳过。"""
        mock_mgr = AsyncMock()
        mock_mgr.acquire_sync_lock.return_value = False
        mock_build.return_value = mock_mgr

        await retry_failed_stocks_job()

        mock_mgr.get_failed_stocks.assert_not_called()

    @patch("app.scheduler.jobs._build_manager")
    async def test_no_failed_stocks(self, mock_build) -> None:
        """无失败股票时直接返回。"""
        mock_mgr = AsyncMock()
        mock_mgr.acquire_sync_lock.return_value = True
        mock_mgr.get_failed_stocks.return_value = []
        mock_build.return_value = mock_mgr

        await retry_failed_stocks_job()

        mock_mgr.release_sync_lock.assert_called_once()

    @patch("app.scheduler.jobs.pipeline_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs._build_manager")
    async def test_retry_success_triggers_pipeline(self, mock_build, mock_pipeline) -> None:
        """重试成功且完成率达标时补跑策略。"""
        mock_mgr = AsyncMock()
        mock_mgr.acquire_sync_lock.return_value = True
        mock_mgr.get_failed_stocks.side_effect = [
            # 第一次调用：可重试的失败股票
            [{"ts_code": "600519.SH", "data_date": date(2026, 1, 1), "retry_count": 1}],
            # 第二次调用（检查超过上限的）
            [{"ts_code": "600519.SH", "data_date": date(2026, 1, 1), "retry_count": 1}],
        ]
        mock_mgr.process_single_stock = AsyncMock()
        mock_mgr.get_sync_summary.return_value = {
            "total": 100, "data_done": 100, "indicator_done": 100,
            "failed": 0, "completion_rate": 0.98,
        }
        mock_build.return_value = mock_mgr

        # Mock session for retry_count increment
        mock_session = AsyncMock()
        mock_mgr.session_factory = AsyncMock()
        mock_mgr.session_factory.return_value.__aenter__.return_value = mock_session

        await retry_failed_stocks_job()

        mock_pipeline.assert_called_once()
        mock_mgr.release_sync_lock.assert_called_once()

    @patch("app.scheduler.jobs.pipeline_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs._build_manager")
    async def test_retry_below_threshold_skips_pipeline(self, mock_build, mock_pipeline) -> None:
        """重试后完成率不达标时跳过策略。"""
        mock_mgr = AsyncMock()
        mock_mgr.acquire_sync_lock.return_value = True
        mock_mgr.get_failed_stocks.side_effect = [
            [{"ts_code": "600519.SH", "data_date": date(2026, 1, 1), "retry_count": 1}],
            [{"ts_code": "600519.SH", "data_date": date(2026, 1, 1), "retry_count": 1}],
        ]
        mock_mgr.process_single_stock = AsyncMock()
        mock_mgr.get_sync_summary.return_value = {
            "total": 100, "data_done": 80, "indicator_done": 80,
            "failed": 20, "completion_rate": 0.80,
        }
        mock_build.return_value = mock_mgr

        mock_session = AsyncMock()
        mock_mgr.session_factory = AsyncMock()
        mock_mgr.session_factory.return_value.__aenter__.return_value = mock_session

        await retry_failed_stocks_job()

        mock_pipeline.assert_not_called()
        mock_mgr.release_sync_lock.assert_called_once()

    @patch("app.scheduler.jobs._build_manager")
    async def test_lock_released_on_error(self, mock_build) -> None:
        """异常时仍释放锁。"""
        mock_mgr = AsyncMock()
        mock_mgr.acquire_sync_lock.return_value = True
        mock_mgr.get_failed_stocks.side_effect = Exception("DB error")
        mock_build.return_value = mock_mgr

        with pytest.raises(Exception, match="DB error"):
            await retry_failed_stocks_job()

        mock_mgr.release_sync_lock.assert_called_once()
