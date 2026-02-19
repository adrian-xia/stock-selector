"""测试批量数据拉取（Task 5.4）。"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.manager import DataManager


def _make_manager(session_factory=None):
    sf = session_factory or AsyncMock()
    return DataManager(
        session_factory=sf,
        clients={"tushare": AsyncMock()},
        primary="tushare",
    )


class TestSyncStockDataInBatches:
    """测试 sync_stock_data_in_batches()。"""

    async def test_single_batch(self) -> None:
        """日期范围 < batch_days 时只调用一次 sync_daily。"""
        mgr = _make_manager()
        mgr.sync_daily = AsyncMock(return_value={"inserted": 10})
        mgr.update_data_progress = AsyncMock()
        mgr.update_stock_status = AsyncMock()

        start = date(2026, 1, 1)
        end = date(2026, 1, 30)
        await mgr.sync_stock_data_in_batches("600519.SH", start, end, batch_days=365)

        mgr.sync_daily.assert_called_once_with("600519.SH", start, end)
        mgr.update_data_progress.assert_called_once_with("600519.SH", end)

    async def test_multiple_batches(self) -> None:
        """日期范围 > batch_days 时分多批调用。"""
        mgr = _make_manager()
        mgr.sync_daily = AsyncMock(return_value={"inserted": 5})
        mgr.update_data_progress = AsyncMock()
        mgr.update_stock_status = AsyncMock()

        start = date(2025, 1, 1)
        end = date(2026, 2, 13)
        await mgr.sync_stock_data_in_batches("600519.SH", start, end, batch_days=365)

        # 2025-01-01 ~ 2025-12-31 (365天), 2026-01-01 ~ 2026-02-13
        assert mgr.sync_daily.call_count == 2
        # 两批都有数据（inserted=5），所以都推进 data_date
        assert mgr.update_data_progress.call_count == 2

    async def test_zero_inserted_skips_progress(self) -> None:
        """写入 0 条时不推进 data_date（防止虚标）。"""
        mgr = _make_manager()
        mgr.sync_daily = AsyncMock(return_value={"inserted": 0})
        mgr.update_data_progress = AsyncMock()
        mgr.update_stock_status = AsyncMock()

        await mgr.sync_stock_data_in_batches(
            "600519.SH", date(2026, 1, 1), date(2026, 1, 30)
        )

        mgr.update_data_progress.assert_not_called()

    async def test_failure_marks_failed(self) -> None:
        """单批失败时标记 status='failed' 并抛出异常。"""
        mgr = _make_manager()
        mgr.sync_daily = AsyncMock(side_effect=Exception("API error"))
        mgr.update_data_progress = AsyncMock()
        mgr.update_stock_status = AsyncMock()

        with pytest.raises(Exception, match="API error"):
            await mgr.sync_stock_data_in_batches(
                "600519.SH", date(2026, 1, 1), date(2026, 1, 30)
            )

        mgr.update_stock_status.assert_called_once_with(
            "600519.SH", "failed", error_message="API error"
        )

    async def test_resume_from_checkpoint(self) -> None:
        """断点续传：从上次 data_date+1 开始。"""
        mgr = _make_manager()
        mgr.sync_daily = AsyncMock(return_value={"inserted": 5})
        mgr.update_data_progress = AsyncMock()

        # 模拟从 2026-02-01 续传到 2026-02-13
        start = date(2026, 2, 1)
        end = date(2026, 2, 13)
        await mgr.sync_stock_data_in_batches("600519.SH", start, end)

        mgr.sync_daily.assert_called_once_with("600519.SH", start, end)
