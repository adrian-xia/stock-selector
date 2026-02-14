"""测试进度管理方法（Task 3.10）。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.manager import DataManager


def _make_manager_with_session(mock_session):
    """创建测试用 DataManager，使用 MagicMock session factory。"""
    sf = MagicMock()
    sf.return_value.__aenter__.return_value = mock_session
    return DataManager(
        session_factory=sf,
        clients={"baostock": AsyncMock()},
        primary="baostock",
    )


class TestResetStaleStatus:
    """测试 reset_stale_status()。"""

    async def test_resets_syncing_and_computing(self) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        count = await mgr.reset_stale_status()

        assert count == 3
        mock_session.commit.assert_called_once()

    async def test_returns_zero_when_none_stale(self) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        count = await mgr.reset_stale_status()

        assert count == 0


class TestInitSyncProgress:
    """测试 init_sync_progress()。"""

    async def test_creates_records_for_listed_stocks(self) -> None:
        mock_session = AsyncMock()
        # 第一次 execute: 查询股票列表
        stock_result = MagicMock()
        stock_result.all.return_value = [("600519.SH",), ("000001.SZ",)]
        # 第二次 execute: INSERT ON CONFLICT
        insert_result = MagicMock()
        insert_result.rowcount = 2
        mock_session.execute.side_effect = [stock_result, insert_result]

        mgr = _make_manager_with_session(mock_session)
        result = await mgr.init_sync_progress()

        assert result["total_stocks"] == 2
        assert result["new_records"] == 2
        mock_session.commit.assert_called_once()

    async def test_returns_zero_when_no_stocks(self) -> None:
        mock_session = AsyncMock()
        stock_result = MagicMock()
        stock_result.all.return_value = []
        mock_session.execute.return_value = stock_result

        mgr = _make_manager_with_session(mock_session)
        result = await mgr.init_sync_progress()

        assert result == {"total_stocks": 0, "new_records": 0}


class TestGetStocksNeedingSync:
    """测试 get_stocks_needing_sync()。"""

    async def test_returns_codes_with_old_data_date(self) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("600519.SH",), ("000001.SZ",)]
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        codes = await mgr.get_stocks_needing_sync(date(2026, 2, 13))

        assert codes == ["600519.SH", "000001.SZ"]

    async def test_returns_empty_when_all_synced(self) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        codes = await mgr.get_stocks_needing_sync(date(2026, 2, 13))

        assert codes == []


class TestGetSyncSummary:
    """测试 get_sync_summary()。"""

    async def test_calculates_completion_rate(self) -> None:
        mock_session = AsyncMock()
        # 5 次 execute 调用：total, data_done, indicator_done, failed, both_done
        total_r = MagicMock(); total_r.scalar.return_value = 100
        data_r = MagicMock(); data_r.scalar.return_value = 95
        ind_r = MagicMock(); ind_r.scalar.return_value = 90
        failed_r = MagicMock(); failed_r.scalar.return_value = 2
        both_r = MagicMock(); both_r.scalar.return_value = 88
        mock_session.execute.side_effect = [total_r, data_r, ind_r, failed_r, both_r]

        mgr = _make_manager_with_session(mock_session)
        summary = await mgr.get_sync_summary(date(2026, 2, 13))

        assert summary["total"] == 100
        assert summary["data_done"] == 95
        assert summary["indicator_done"] == 90
        assert summary["failed"] == 2
        assert summary["completion_rate"] == 0.88

    async def test_returns_zero_when_no_stocks(self) -> None:
        mock_session = AsyncMock()
        total_r = MagicMock(); total_r.scalar.return_value = 0
        mock_session.execute.return_value = total_r

        mgr = _make_manager_with_session(mock_session)
        summary = await mgr.get_sync_summary(date(2026, 2, 13))

        assert summary["completion_rate"] == 0.0


class TestGetFailedStocks:
    """测试 get_failed_stocks()。"""

    async def test_returns_retryable_stocks(self) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("600519.SH", date(2026, 1, 1), 1),
            ("000001.SZ", date(2026, 1, 5), 2),
        ]
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        stocks = await mgr.get_failed_stocks(max_retries=3)

        assert len(stocks) == 2
        assert stocks[0]["ts_code"] == "600519.SH"
        assert stocks[0]["retry_count"] == 1


class TestUpdateStockStatus:
    """测试 update_stock_status()。"""

    async def test_updates_status_and_error(self) -> None:
        mock_session = AsyncMock()
        mgr = _make_manager_with_session(mock_session)
        await mgr.update_stock_status("600519.SH", "failed", "timeout")

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


class TestShouldHaveData:
    """测试 should_have_data() 静态方法。"""

    def test_stock_before_listing(self) -> None:
        stock = {"list_date": date(2020, 1, 1)}
        assert DataManager.should_have_data(stock, date(2019, 12, 31)) is False

    def test_stock_after_listing(self) -> None:
        stock = {"list_date": date(2020, 1, 1)}
        assert DataManager.should_have_data(stock, date(2020, 1, 1)) is True

    def test_stock_after_delisting(self) -> None:
        stock = {"list_date": date(2020, 1, 1), "delist_date": date(2025, 1, 1)}
        assert DataManager.should_have_data(stock, date(2025, 1, 1)) is False

    def test_stock_before_delisting(self) -> None:
        stock = {"list_date": date(2020, 1, 1), "delist_date": date(2025, 1, 1)}
        assert DataManager.should_have_data(stock, date(2024, 12, 31)) is True

    def test_stock_no_dates(self) -> None:
        stock = {}
        assert DataManager.should_have_data(stock, date(2026, 1, 1)) is True
