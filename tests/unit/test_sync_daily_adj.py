"""sync-daily CLI 命令单元测试（Tushare 按日期全市场模式）。"""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from app.data.cli import cli


class TestSyncDailyTushare:
    """验证 sync-daily 使用 Tushare 按日期全市场模式。"""

    @patch("app.data.cli._build_manager")
    def test_sync_daily_calls_raw_and_etl(self, mock_mgr) -> None:
        """sync-daily 应调用 sync_raw_daily + etl_daily。"""
        manager = MagicMock()
        manager.is_trade_day = AsyncMock(return_value=True)
        manager.sync_raw_daily = AsyncMock(
            return_value={"daily": 5000, "adj_factor": 5000, "daily_basic": 5000}
        )
        manager.etl_daily = AsyncMock(return_value={"inserted": 5000})
        mock_mgr.return_value = manager

        runner = CliRunner()
        result = runner.invoke(cli, ["sync-daily"])

        assert result.exit_code == 0
        manager.sync_raw_daily.assert_called_once()
        manager.etl_daily.assert_called_once()

    @patch("app.data.cli._build_manager")
    def test_sync_daily_skip_non_trading_day(self, mock_mgr) -> None:
        """非交易日应跳过同步。"""
        manager = MagicMock()
        manager.is_trade_day = AsyncMock(return_value=False)
        mock_mgr.return_value = manager

        runner = CliRunner()
        result = runner.invoke(cli, ["sync-daily"])

        assert result.exit_code == 0
        assert "not a trading day" in result.output
