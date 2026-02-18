"""参数优化 API 端点测试（mock 优化器）。"""

import pytest

from app.optimization.param_space import count_combinations
from app.strategy.factory import STRATEGY_REGISTRY, StrategyFactory


class TestStrategyParamSpace:
    """策略参数空间注册测试。"""

    def test_all_strategies_have_param_space(self) -> None:
        """所有有 default_params 的策略都应有 param_space。"""
        for name, meta in STRATEGY_REGISTRY.items():
            if meta.default_params:
                assert meta.param_space, f"策略 {name} 有 default_params 但缺少 param_space"

    def test_param_space_keys_match_default_params(self) -> None:
        """param_space 的键应该是 default_params 的子集。"""
        for name, meta in STRATEGY_REGISTRY.items():
            if meta.param_space:
                for key in meta.param_space:
                    assert key in meta.default_params, (
                        f"策略 {name} 的 param_space 键 '{key}' 不在 default_params 中"
                    )

    def test_param_space_valid_format(self) -> None:
        """param_space 格式正确。"""
        for name, meta in STRATEGY_REGISTRY.items():
            for param_name, spec in meta.param_space.items():
                assert "type" in spec, f"{name}.{param_name} 缺少 type"
                assert spec["type"] in ("int", "float"), f"{name}.{param_name} type 无效"
                assert "min" in spec, f"{name}.{param_name} 缺少 min"
                assert "max" in spec, f"{name}.{param_name} 缺少 max"
                assert "step" in spec, f"{name}.{param_name} 缺少 step"
                assert spec["min"] <= spec["max"], f"{name}.{param_name} min > max"
                assert spec["step"] > 0, f"{name}.{param_name} step <= 0"

    def test_default_params_in_range(self) -> None:
        """default_params 的值应在 param_space 范围内。"""
        for name, meta in STRATEGY_REGISTRY.items():
            for param_name, spec in meta.param_space.items():
                default_val = meta.default_params.get(param_name)
                if default_val is not None:
                    assert spec["min"] <= default_val <= spec["max"], (
                        f"策略 {name} 的 {param_name} 默认值 {default_val} "
                        f"不在范围 [{spec['min']}, {spec['max']}] 内"
                    )

    def test_grid_combinations_reasonable(self) -> None:
        """每个策略的网格搜索组合数不超过 10000。"""
        for name, meta in STRATEGY_REGISTRY.items():
            if meta.param_space:
                combos = count_combinations(meta.param_space)
                assert combos <= 10000, (
                    f"策略 {name} 的默认参数空间组合数 {combos} 超过 10000"
                )


class TestStrategyMetaParamSpace:
    """StrategyMeta param_space 字段测试。"""

    def test_get_meta_includes_param_space(self) -> None:
        """get_meta 返回的元数据包含 param_space。"""
        meta = StrategyFactory.get_meta("ma-cross")
        assert meta.param_space
        assert "fast" in meta.param_space
        assert "slow" in meta.param_space

    def test_strategy_without_params_has_empty_space(self) -> None:
        """无参数策略的 param_space 为空或不含键。"""
        # macd-golden 和 boll-breakthrough 没有 default_params
        meta = StrategyFactory.get_meta("macd-golden")
        assert meta.param_space == {} or not meta.param_space

    def test_28_strategies_registered(self) -> None:
        """确认 28 种策略已注册。"""
        assert len(STRATEGY_REGISTRY) == 28

    def test_technical_strategies_count(self) -> None:
        """16 种技术面策略。"""
        technical = StrategyFactory.get_by_category("technical")
        assert len(technical) == 16

    def test_fundamental_strategies_count(self) -> None:
        """12 种基本面策略。"""
        fundamental = StrategyFactory.get_by_category("fundamental")
        assert len(fundamental) == 12
