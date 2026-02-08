"""sync-daily 复权因子集成测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from app.data.cli import cli


class TestSyncDailyAdjFactor:
    """验证 sync-daily 流程包含复权因子同步。"""

    @patch("app.data.adj_factor.batch_update_adj_factor", new_callable=AsyncMock, return_value=1)
    @patch("app.data.cli.BaoStockClient")
    @patch("app.data.cli.async_session_factory")
    @patch("app.data.cli._build_manager")
    def test_sync_daily_includes_adj_factor(
        self, mock_mgr, mock_sf, mock_bs_cls, mock_batch_update
    ) -> None:
        """sync-daily 应在日线同步后同步复权因子。"""
        manager = MagicMock()
        manager.is_trade_day = AsyncMock(return_value=True)
        manager.get_stock_list = AsyncMock(return_value=[
            {"ts_code": "600519.SH", "list_date": "2001-08-27"},
        ])
        manager.sync_daily = AsyncMock()
        mock_mgr.return_value = manager

        # mock BaoStockClient 实例
        bs_instance = MagicMock()
        bs_instance.fetch_adj_factor = AsyncMock(return_value=[
            {"ts_code": "600519.SH", "trade_date": "2026-02-08", "adj_factor": 1.0},
        ])
        mock_bs_cls.return_value = bs_instance

        runner = CliRunner()
        result = runner.invoke(cli, ["sync-daily"])

        assert result.exit_code == 0
        # 验证日线同步被调用
        manager.sync_daily.assert_called_once()
        # 验证复权因子获取被调用
        bs_instance.fetch_adj_factor.assert_called_once()
        # 验证批量更新被调用
        mock_batch_update.assert_called_once()
        # 输出应包含 adj_factor_updated
        assert "adj_factor_updated" in result.output

    @patch("app.data.cli.BaoStockClient")
    @patch("app.data.cli.async_session_factory")
    @patch("app.data.cli._build_manager")
    def test_sync_daily_skip_non_trading_day(
        self, mock_mgr, mock_sf, mock_bs_cls
    ) -> None:
        """非交易日应跳过同步。"""
        manager = MagicMock()
        manager.is_trade_day = AsyncMock(return_value=False)
        mock_mgr.return_value = manager

        runner = CliRunner()
        result = runner.invoke(cli, ["sync-daily"])

        assert result.exit_code == 0
        assert "not a trading day" in result.output
