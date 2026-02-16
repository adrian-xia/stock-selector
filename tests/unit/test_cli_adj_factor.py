"""sync-adj-factor CLI 命令单元测试。"""

from click.testing import CliRunner

from app.data.cli import cli


class TestSyncAdjFactorCLI:
    """sync-adj-factor 命令测试（Tushare 模式下已简化）。"""

    def test_help_text(self) -> None:
        """--help 应显示命令说明。"""
        runner = CliRunner()
        result = runner.invoke(cli, ["sync-adj-factor", "--help"])
        assert result.exit_code == 0
        assert "复权因子" in result.output

    def test_prints_tushare_message(self) -> None:
        """Tushare 模式下应提示使用 backfill-daily。"""
        runner = CliRunner()
        result = runner.invoke(cli, ["sync-adj-factor"])
        assert result.exit_code == 0
        assert "Tushare" in result.output

    def test_force_flag_accepted(self) -> None:
        """--force 参数应被接受。"""
        runner = CliRunner()
        result = runner.invoke(cli, ["sync-adj-factor", "--force"])
        assert result.exit_code == 0
