"""sync-adj-factor CLI 命令单元测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from app.data.cli import cli


class TestSyncAdjFactorCLI:
    """sync-adj-factor 命令测试。"""

    def test_help_text(self) -> None:
        """--help 应显示命令说明。"""
        runner = CliRunner()
        result = runner.invoke(cli, ["sync-adj-factor", "--help"])
        assert result.exit_code == 0
        assert "复权因子" in result.output

    @patch("app.data.cli.async_session_factory")
    @patch("app.data.cli.BaoStockClient")
    @patch("app.data.cli._build_manager")
    def test_force_flag_accepted(self, mock_mgr, mock_bs, mock_sf) -> None:
        """--force 参数应被接受。"""
        manager = MagicMock()
        manager.get_stock_list = AsyncMock(return_value=[])
        mock_mgr.return_value = manager

        runner = CliRunner()
        result = runner.invoke(cli, ["sync-adj-factor", "--force"])
        assert result.exit_code == 0
        assert "强制刷新" in result.output

    @patch("app.data.cli.async_session_factory")
    @patch("app.data.cli.BaoStockClient")
    @patch("app.data.cli._build_manager")
    def test_skip_when_all_populated(self, mock_mgr, mock_bs, mock_sf) -> None:
        """所有股票已有复权因子时应跳过。"""
        manager = MagicMock()
        manager.get_stock_list = AsyncMock(return_value=[
            {"ts_code": "600519.SH", "list_date": "2001-08-27"},
        ])
        mock_mgr.return_value = manager

        # 模拟 async with session_factory() as session
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []  # 没有 NULL adj_factor 的股票
        session.execute.return_value = result_mock

        ctx = AsyncMock()
        ctx.__aenter__.return_value = session
        ctx.__aexit__.return_value = False
        mock_sf.return_value = ctx

        runner = CliRunner()
        result = runner.invoke(cli, ["sync-adj-factor"])
        assert result.exit_code == 0
        assert "无需同步" in result.output
