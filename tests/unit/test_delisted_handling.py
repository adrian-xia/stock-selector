"""测试退市处理（Task 11.5）。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.manager import DataManager


def _make_manager_with_session(mock_session):
    sf = MagicMock()
    sf.return_value.__aenter__.return_value = mock_session
    return DataManager(
        session_factory=sf,
        clients={"tushare": AsyncMock()},
        primary="tushare",
    )


class TestMarkStockDelisted:
    """测试 mark_stock_delisted()。"""

    async def test_updates_both_tables(self) -> None:
        """事务中同时更新 stocks 表和 progress 表。"""
        mock_session = AsyncMock()
        mgr = _make_manager_with_session(mock_session)
        await mgr.mark_stock_delisted("600519.SH", date(2026, 1, 1))

        # 两次 execute（stocks + progress）+ 一次 commit
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()


class TestSyncDelistedStatus:
    """测试 sync_delisted_status()。"""

    async def test_forward_and_reverse_sync(self) -> None:
        """正向标记退市 + 反向恢复。"""
        mock_session = AsyncMock()
        forward_result = MagicMock()
        forward_result.rowcount = 3
        reverse_result = MagicMock()
        reverse_result.rowcount = 1
        mock_session.execute.side_effect = [forward_result, reverse_result]

        mgr = _make_manager_with_session(mock_session)
        result = await mgr.sync_delisted_status()

        assert result == {"newly_delisted": 3, "restored": 1}
        mock_session.commit.assert_called_once()

    async def test_no_changes(self) -> None:
        """无变更时返回零。"""
        mock_session = AsyncMock()
        forward_result = MagicMock()
        forward_result.rowcount = 0
        reverse_result = MagicMock()
        reverse_result.rowcount = 0
        mock_session.execute.side_effect = [forward_result, reverse_result]

        mgr = _make_manager_with_session(mock_session)
        result = await mgr.sync_delisted_status()

        assert result == {"newly_delisted": 0, "restored": 0}
