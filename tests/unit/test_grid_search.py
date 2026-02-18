"""网格搜索优化器测试（mock 回测引擎）。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.optimization.grid_search import GridSearchOptimizer, _extract_result


def _mock_bt_result(sharpe: float | None = 1.0, annual_return: float | None = 0.15) -> dict:
    """构造 mock 回测结果。"""
    strat = MagicMock()

    # mock analyzers
    sharpe_analyzer = MagicMock()
    sharpe_analyzer.get_analysis.return_value = {"sharperatio": sharpe}
    strat.analyzers.sharpe = sharpe_analyzer

    dd_analyzer = MagicMock()
    dd_analyzer.get_analysis.return_value = {"max": {"drawdown": 10.0}}
    strat.analyzers.drawdown = dd_analyzer

    trade_analyzer = MagicMock()
    trade_analyzer.get_analysis.return_value = {
        "total": {"total": 20},
        "won": {"total": 12},
    }
    strat.analyzers.trades = trade_analyzer

    returns_analyzer = MagicMock()
    returns_analyzer.get_analysis.return_value = {
        "rnorm100": (annual_return * 100) if annual_return is not None else None,
    }
    strat.analyzers.returns = returns_analyzer

    return {
        "strategy_instance": strat,
        "equity_curve": [{"value": 1000000}, {"value": 1150000}],
        "trades_log": [],
        "elapsed_ms": 100,
    }


class TestGridSearchOptimizer:
    """GridSearchOptimizer 测试。"""

    @pytest.mark.asyncio
    @patch("app.optimization.grid_search.run_backtest")
    async def test_basic_grid_search(self, mock_run: AsyncMock) -> None:
        """基本网格搜索返回排序结果。"""
        mock_run.return_value = _mock_bt_result(sharpe=1.5)

        optimizer = GridSearchOptimizer(session_factory=MagicMock())
        results = await optimizer.optimize(
            strategy_name="ma-cross",
            param_space={"fast": {"type": "int", "min": 3, "max": 5, "step": 1}},
            stock_codes=["600519.SH"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert len(results) == 3
        assert mock_run.call_count == 3

    @pytest.mark.asyncio
    @patch("app.optimization.grid_search.run_backtest")
    async def test_results_sorted_by_sharpe(self, mock_run: AsyncMock) -> None:
        """结果按 sharpe_ratio 降序排列。"""
        sharpe_values = [0.5, 2.0, 1.0]
        mock_run.side_effect = [
            _mock_bt_result(sharpe=s) for s in sharpe_values
        ]

        optimizer = GridSearchOptimizer(session_factory=MagicMock())
        results = await optimizer.optimize(
            strategy_name="rsi-oversold",
            param_space={"period": {"type": "int", "min": 3, "max": 5, "step": 1}},
            stock_codes=["600519.SH"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        sharpes = [r.sharpe_ratio for r in results]
        assert sharpes == [2.0, 1.0, 0.5]

    @pytest.mark.asyncio
    @patch("app.optimization.grid_search.run_backtest")
    async def test_failed_backtest_skipped(self, mock_run: AsyncMock) -> None:
        """回测失败的组合被跳过。"""
        mock_run.side_effect = [
            _mock_bt_result(sharpe=1.0),
            Exception("回测失败"),
            _mock_bt_result(sharpe=2.0),
        ]

        optimizer = GridSearchOptimizer(session_factory=MagicMock())
        results = await optimizer.optimize(
            strategy_name="ma-cross",
            param_space={"fast": {"type": "int", "min": 3, "max": 5, "step": 1}},
            stock_codes=["600519.SH"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    @patch("app.optimization.grid_search.run_backtest")
    async def test_progress_callback(self, mock_run: AsyncMock) -> None:
        """进度回调被正确调用。"""
        mock_run.return_value = _mock_bt_result()
        progress_calls: list[tuple[int, int]] = []

        optimizer = GridSearchOptimizer(session_factory=MagicMock())
        await optimizer.optimize(
            strategy_name="ma-cross",
            param_space={"fast": {"type": "int", "min": 3, "max": 5, "step": 1}},
            stock_codes=["600519.SH"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            progress_callback=lambda c, t: progress_calls.append((c, t)),
        )

        assert progress_calls == [(1, 3), (2, 3), (3, 3)]

    @pytest.mark.asyncio
    @patch("app.optimization.grid_search.run_backtest")
    async def test_two_param_combinations(self, mock_run: AsyncMock) -> None:
        """两个参数的笛卡尔积组合数正确。"""
        mock_run.return_value = _mock_bt_result()

        optimizer = GridSearchOptimizer(session_factory=MagicMock())
        results = await optimizer.optimize(
            strategy_name="ma-cross",
            param_space={
                "fast": {"type": "int", "min": 3, "max": 5, "step": 1},
                "slow": {"type": "int", "min": 10, "max": 20, "step": 5},
            },
            stock_codes=["600519.SH"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert len(results) == 9
        assert mock_run.call_count == 9


class TestExtractResult:
    """_extract_result 测试。"""

    def test_extract_metrics(self) -> None:
        """正确提取回测指标。"""
        bt = _mock_bt_result(sharpe=1.5, annual_return=0.2)
        result = _extract_result({"fast": 5}, bt)

        assert result.params == {"fast": 5}
        assert result.sharpe_ratio == 1.5
        assert result.annual_return == 0.2
        assert result.max_drawdown is not None
        assert result.win_rate == 0.6  # 12/20
        assert result.total_trades == 20
