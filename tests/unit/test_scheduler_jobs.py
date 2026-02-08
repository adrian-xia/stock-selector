"""测试调度器任务逻辑。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler.jobs import run_post_market_chain, sync_daily_step


class TestRunPostMarketChain:
    """测试盘后链路。"""

    @patch("app.scheduler.jobs._build_manager")
    async def test_skip_non_trading_day(
        self, mock_build: MagicMock
    ) -> None:
        """非交易日应跳过整个链路。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = False
        mock_build.return_value = mock_mgr

        await run_post_market_chain(date(2024, 1, 6))  # 周六

        mock_mgr.is_trade_day.assert_called_once_with(date(2024, 1, 6))
        # 不应调用任何同步方法
        mock_mgr.get_stock_list.assert_not_called()

    @patch("app.scheduler.jobs.pipeline_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs.indicator_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs.sync_daily_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs._build_manager")
    async def test_full_chain_on_trading_day(
        self,
        mock_build: MagicMock,
        mock_sync: AsyncMock,
        mock_indicator: AsyncMock,
        mock_pipeline: AsyncMock,
    ) -> None:
        """交易日应按顺序执行全部步骤。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = True
        mock_build.return_value = mock_mgr

        target = date(2024, 1, 8)  # 周一
        await run_post_market_chain(target)

        mock_sync.assert_called_once()
        mock_indicator.assert_called_once_with(target)
        mock_pipeline.assert_called_once_with(target)

    @patch("app.scheduler.jobs.indicator_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs.sync_daily_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs._build_manager")
    async def test_chain_stops_on_sync_failure(
        self,
        mock_build: MagicMock,
        mock_sync: AsyncMock,
        mock_indicator: AsyncMock,
    ) -> None:
        """日线同步失败时应中断链路，不执行后续步骤。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = True
        mock_build.return_value = mock_mgr

        mock_sync.side_effect = RuntimeError("sync failed")

        await run_post_market_chain(date(2024, 1, 8))

        mock_sync.assert_called_once()
        # indicator_step 不应被调用
        mock_indicator.assert_not_called()


class TestSyncDailyStep:
    """测试日线同步步骤。"""

    async def test_sync_all_stocks(self) -> None:
        """应逐只同步所有上市股票。"""
        mock_mgr = AsyncMock()
        mock_mgr.get_stock_list.return_value = [
            {"ts_code": "600519.SH", "name": "贵州茅台"},
            {"ts_code": "000858.SZ", "name": "五粮液"},
        ]
        mock_mgr.sync_daily.return_value = {"inserted": 1}

        await sync_daily_step(date(2024, 1, 8), manager=mock_mgr)

        assert mock_mgr.sync_daily.call_count == 2

    async def test_partial_failure_continues(self) -> None:
        """部分股票同步失败不应中断其他股票。"""
        mock_mgr = AsyncMock()
        mock_mgr.get_stock_list.return_value = [
            {"ts_code": "600519.SH", "name": "贵州茅台"},
            {"ts_code": "000858.SZ", "name": "五粮液"},
            {"ts_code": "300750.SZ", "name": "宁德时代"},
        ]
        # 第二只股票失败
        mock_mgr.sync_daily.side_effect = [
            {"inserted": 1},
            RuntimeError("timeout"),
            {"inserted": 1},
        ]

        # 不应抛出异常
        await sync_daily_step(date(2024, 1, 8), manager=mock_mgr)

        # 三只股票都应尝试同步
        assert mock_mgr.sync_daily.call_count == 3
