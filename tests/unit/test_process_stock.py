"""测试单只股票完整处理流程（Task 7.4）。"""

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


class TestProcessSingleStock:
    """测试 process_single_stock()。"""

    @patch("app.config.settings")
    async def test_full_flow_new_stock(self, mock_settings) -> None:
        """新股（data_date=1900-01-01）从 data_start_date 开始同步。"""
        mock_settings.data_start_date = "2024-01-01"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (date(1900, 1, 1), date(1900, 1, 1))
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        mgr.sync_stock_data_in_batches = AsyncMock()
        mgr.compute_indicators_in_batches = AsyncMock()
        mgr.update_stock_status = AsyncMock()

        await mgr.process_single_stock("600519.SH", date(2026, 2, 13))

        # 数据拉取从 data_start_date 开始
        mgr.sync_stock_data_in_batches.assert_called_once_with(
            "600519.SH", date(2024, 1, 1), date(2026, 2, 13), batch_days=365
        )
        # 指标计算也从 data_start_date 开始
        mgr.compute_indicators_in_batches.assert_called_once_with(
            "600519.SH", date(2024, 1, 1), date(2026, 2, 13), batch_days=365
        )
        # 最终状态设为 idle
        assert mgr.update_stock_status.call_args_list[-1].args == ("600519.SH", "idle")

    @patch("app.config.settings")
    async def test_incremental_sync(self, mock_settings) -> None:
        """增量同步：从 data_date+1 开始。"""
        mock_settings.data_start_date = "2024-01-01"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (date(2026, 2, 10), date(2026, 2, 10))
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        mgr.sync_stock_data_in_batches = AsyncMock()
        mgr.compute_indicators_in_batches = AsyncMock()
        mgr.update_stock_status = AsyncMock()

        await mgr.process_single_stock("600519.SH", date(2026, 2, 13))

        mgr.sync_stock_data_in_batches.assert_called_once_with(
            "600519.SH", date(2026, 2, 11), date(2026, 2, 13), batch_days=365
        )

    @patch("app.config.settings")
    async def test_skip_when_no_progress_record(self, mock_settings) -> None:
        """无进度记录时跳过。"""
        mock_settings.data_start_date = "2024-01-01"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        mgr.sync_stock_data_in_batches = AsyncMock()

        await mgr.process_single_stock("600519.SH", date(2026, 2, 13))

        mgr.sync_stock_data_in_batches.assert_not_called()

    @patch("app.config.settings")
    async def test_already_up_to_date(self, mock_settings) -> None:
        """已是最新时不执行同步。"""
        mock_settings.data_start_date = "2024-01-01"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (date(2026, 2, 13), date(2026, 2, 13))
        mock_session.execute.return_value = mock_result

        mgr = _make_manager_with_session(mock_session)
        mgr.sync_stock_data_in_batches = AsyncMock()
        mgr.compute_indicators_in_batches = AsyncMock()
        mgr.update_stock_status = AsyncMock()

        await mgr.process_single_stock("600519.SH", date(2026, 2, 13))

        mgr.sync_stock_data_in_batches.assert_not_called()
        mgr.compute_indicators_in_batches.assert_not_called()


class TestProcessStocksBatch:
    """测试 process_stocks_batch()。"""

    async def test_concurrent_processing(self) -> None:
        """并发处理多只股票。"""
        sf = MagicMock()
        mgr = DataManager(
            session_factory=sf,
            clients={"baostock": AsyncMock()},
            primary="baostock",
        )
        mgr.process_single_stock = AsyncMock()

        stocks = ["600519.SH", "000001.SZ", "000002.SZ"]
        result = await mgr.process_stocks_batch(stocks, date(2026, 2, 13), concurrency=2)

        assert result["success"] == 3
        assert result["failed"] == 0
        assert result["timeout"] is False
        assert mgr.process_single_stock.call_count == 3

    async def test_partial_failure(self) -> None:
        """部分股票失败不影响其他。"""
        sf = MagicMock()
        mgr = DataManager(
            session_factory=sf,
            clients={"baostock": AsyncMock()},
            primary="baostock",
        )

        async def _mock_process(code, target):
            if code == "000001.SZ":
                raise Exception("fail")

        mgr.process_single_stock = _mock_process

        stocks = ["600519.SH", "000001.SZ", "000002.SZ"]
        result = await mgr.process_stocks_batch(stocks, date(2026, 2, 13))

        assert result["success"] == 2
        assert result["failed"] == 1
