"""测试批量指标计算（Task 6.3）。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.manager import DataManager


def _make_manager_with_session(mock_session):
    sf = MagicMock()
    sf.return_value.__aenter__.return_value = mock_session
    return DataManager(
        session_factory=sf,
        clients={"baostock": AsyncMock()},
        primary="baostock",
    )


class TestComputeIndicatorsInBatches:
    """测试 compute_indicators_in_batches()。"""

    async def test_no_data_updates_progress(self) -> None:
        """无数据时仍更新 indicator_date。"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        mgr.update_indicator_progress = AsyncMock()
        mgr.update_stock_status = AsyncMock()

        await mgr.compute_indicators_in_batches(
            "600519.SH", date(2026, 1, 1), date(2026, 1, 30)
        )

        mgr.update_indicator_progress.assert_called_once_with("600519.SH", date(2026, 1, 30))

    async def test_failure_marks_failed(self) -> None:
        """计算失败时标记 status='failed'。"""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB error")

        mgr = _make_manager_with_session(mock_session)
        mgr.update_stock_status = AsyncMock()

        with pytest.raises(Exception, match="DB error"):
            await mgr.compute_indicators_in_batches(
                "600519.SH", date(2026, 1, 1), date(2026, 1, 30)
            )

        mgr.update_stock_status.assert_called_once_with(
            "600519.SH", "failed", error_message="DB error"
        )
