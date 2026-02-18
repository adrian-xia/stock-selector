"""遗传算法优化器测试（mock 回测引擎）。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.optimization.genetic import (
    GeneticOptimizer,
    _crossover,
    _individual_key,
    _mutate,
    _random_individual,
    _tournament_select,
)


def _mock_bt_result(sharpe: float = 1.0) -> dict:
    """构造 mock 回测结果。"""
    strat = MagicMock()
    sharpe_analyzer = MagicMock()
    sharpe_analyzer.get_analysis.return_value = {"sharperatio": sharpe}
    strat.analyzers.sharpe = sharpe_analyzer
    dd_analyzer = MagicMock()
    dd_analyzer.get_analysis.return_value = {"max": {"drawdown": 5.0}}
    strat.analyzers.drawdown = dd_analyzer
    trade_analyzer = MagicMock()
    trade_analyzer.get_analysis.return_value = {
        "total": {"total": 10}, "won": {"total": 6},
    }
    strat.analyzers.trades = trade_analyzer
    returns_analyzer = MagicMock()
    returns_analyzer.get_analysis.return_value = {"rnorm100": 15.0}
    strat.analyzers.returns = returns_analyzer

    return {
        "strategy_instance": strat,
        "equity_curve": [{"value": 1000000}, {"value": 1150000}],
        "trades_log": [],
        "elapsed_ms": 50,
    }


SAMPLE_SPACE = {
    "fast": {"type": "int", "min": 3, "max": 10, "step": 1},
    "slow": {"type": "int", "min": 10, "max": 30, "step": 5},
}


class TestRandomIndividual:
    """_random_individual 测试。"""

    def test_values_in_range(self) -> None:
        for _ in range(50):
            ind = _random_individual(SAMPLE_SPACE)
            assert 3 <= ind["fast"] <= 10
            assert 10 <= ind["slow"] <= 30

    def test_int_type(self) -> None:
        ind = _random_individual(SAMPLE_SPACE)
        assert isinstance(ind["fast"], int)
        assert isinstance(ind["slow"], int)

    def test_step_aligned(self) -> None:
        """值应该对齐到步长。"""
        space = {"x": {"type": "int", "min": 0, "max": 10, "step": 5}}
        for _ in range(50):
            ind = _random_individual(space)
            assert ind["x"] in [0, 5, 10]


class TestTournamentSelect:
    """_tournament_select 测试。"""

    def test_selects_best(self) -> None:
        """锦标赛选择倾向于高适应度个体。"""
        scores = [
            ({"x": 1}, 0.1),
            ({"x": 2}, 0.5),
            ({"x": 3}, 2.0),
        ]
        # 多次选择，最优个体应该出现最多
        counts = {1: 0, 2: 0, 3: 0}
        for _ in range(300):
            winner = _tournament_select(scores, tournament_size=3)
            counts[winner["x"]] += 1
        # tournament_size=3 且只有 3 个，每次都选最优
        assert counts[3] == 300


class TestCrossover:
    """_crossover 测试。"""

    def test_produces_two_children(self) -> None:
        p1 = {"fast": 3, "slow": 10}
        p2 = {"fast": 8, "slow": 25}
        c1, c2 = _crossover(p1, p2, ["fast", "slow"])
        assert set(c1.keys()) == {"fast", "slow"}
        assert set(c2.keys()) == {"fast", "slow"}

    def test_single_param_no_change(self) -> None:
        """单参数时交叉不改变值。"""
        p1 = {"x": 1}
        p2 = {"x": 2}
        c1, c2 = _crossover(p1, p2, ["x"])
        assert c1 == {"x": 1}
        assert c2 == {"x": 2}


class TestMutate:
    """_mutate 测试。"""

    def test_mutation_rate_zero(self) -> None:
        """变异率为 0 时不变。"""
        ind = {"fast": 5, "slow": 20}
        result = _mutate(ind, SAMPLE_SPACE, mutation_rate=0.0)
        assert result == ind

    def test_mutation_rate_one(self) -> None:
        """变异率为 1 时所有参数都变异（值仍在范围内）。"""
        ind = {"fast": 5, "slow": 20}
        for _ in range(20):
            result = _mutate(ind, SAMPLE_SPACE, mutation_rate=1.0)
            assert 3 <= result["fast"] <= 10
            assert 10 <= result["slow"] <= 30


class TestIndividualKey:
    """_individual_key 测试。"""

    def test_same_params_same_key(self) -> None:
        assert _individual_key({"a": 1, "b": 2}) == _individual_key({"b": 2, "a": 1})

    def test_different_params_different_key(self) -> None:
        assert _individual_key({"a": 1}) != _individual_key({"a": 2})


class TestGeneticOptimizer:
    """GeneticOptimizer 集成测试。"""

    @pytest.mark.asyncio
    @patch("app.optimization.genetic.run_backtest")
    async def test_basic_ga(self, mock_run: AsyncMock) -> None:
        """基本遗传算法执行并返回结果。"""
        mock_run.return_value = _mock_bt_result(sharpe=1.0)

        optimizer = GeneticOptimizer(session_factory=MagicMock())
        results = await optimizer.optimize(
            strategy_name="ma-cross",
            param_space=SAMPLE_SPACE,
            stock_codes=["600519.SH"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            ga_config={"population_size": 5, "max_generations": 3},
        )

        assert len(results) > 0
        # 结果按 sharpe 降序
        for i in range(len(results) - 1):
            s1 = results[i].sharpe_ratio or float("-inf")
            s2 = results[i + 1].sharpe_ratio or float("-inf")
            assert s1 >= s2

    @pytest.mark.asyncio
    @patch("app.optimization.genetic.run_backtest")
    async def test_progress_callback(self, mock_run: AsyncMock) -> None:
        """进度回调按代数调用。"""
        mock_run.return_value = _mock_bt_result()
        progress_calls: list[tuple[int, int]] = []

        optimizer = GeneticOptimizer(session_factory=MagicMock())
        await optimizer.optimize(
            strategy_name="ma-cross",
            param_space={"fast": {"type": "int", "min": 3, "max": 5, "step": 1}},
            stock_codes=["600519.SH"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            ga_config={"population_size": 4, "max_generations": 3},
            progress_callback=lambda c, t: progress_calls.append((c, t)),
        )

        assert len(progress_calls) == 3
        assert progress_calls[-1] == (3, 3)
