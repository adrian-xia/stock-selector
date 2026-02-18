"""参数空间工具函数测试。"""

import pytest

from app.optimization.param_space import count_combinations, generate_combinations


class TestGenerateCombinations:
    """generate_combinations 测试。"""

    def test_single_int_param(self) -> None:
        """单个 int 参数生成正确组合。"""
        space = {"period": {"type": "int", "min": 5, "max": 15, "step": 5}}
        result = generate_combinations(space)
        assert result == [{"period": 5}, {"period": 10}, {"period": 15}]

    def test_single_float_param(self) -> None:
        """单个 float 参数生成正确组合。"""
        space = {"ratio": {"type": "float", "min": 1.0, "max": 2.0, "step": 0.5}}
        result = generate_combinations(space)
        assert result == [{"ratio": 1.0}, {"ratio": 1.5}, {"ratio": 2.0}]

    def test_two_params_cartesian(self) -> None:
        """两个参数生成笛卡尔积。"""
        space = {
            "fast": {"type": "int", "min": 3, "max": 5, "step": 1},
            "slow": {"type": "int", "min": 10, "max": 20, "step": 5},
        }
        result = generate_combinations(space)
        assert len(result) == 3 * 3  # 3 × 3 = 9
        # 验证第一个和最后一个
        assert result[0] == {"fast": 3, "slow": 10}
        assert result[-1] == {"fast": 5, "slow": 20}

    def test_empty_space(self) -> None:
        """空参数空间返回单个空字典。"""
        result = generate_combinations({})
        assert result == [{}]

    def test_single_value_range(self) -> None:
        """min == max 时只有一个值。"""
        space = {"x": {"type": "int", "min": 10, "max": 10, "step": 1}}
        result = generate_combinations(space)
        assert result == [{"x": 10}]

    def test_int_type_produces_int(self) -> None:
        """int 类型参数值为 int。"""
        space = {"n": {"type": "int", "min": 1, "max": 3, "step": 1}}
        result = generate_combinations(space)
        for combo in result:
            assert isinstance(combo["n"], int)

    def test_float_precision(self) -> None:
        """float 类型不产生精度问题。"""
        space = {"r": {"type": "float", "min": 0.1, "max": 0.3, "step": 0.1}}
        result = generate_combinations(space)
        assert len(result) == 3
        values = [c["r"] for c in result]
        assert 0.1 in values
        assert 0.2 in values
        assert 0.3 in values


class TestCountCombinations:
    """count_combinations 测试。"""

    def test_single_param(self) -> None:
        space = {"period": {"type": "int", "min": 5, "max": 15, "step": 5}}
        assert count_combinations(space) == 3

    def test_two_params(self) -> None:
        space = {
            "fast": {"type": "int", "min": 3, "max": 5, "step": 1},
            "slow": {"type": "int", "min": 10, "max": 20, "step": 5},
        }
        assert count_combinations(space) == 9

    def test_empty_space(self) -> None:
        assert count_combinations({}) == 1

    def test_matches_generate(self) -> None:
        """count 结果与 generate 长度一致。"""
        space = {
            "a": {"type": "int", "min": 1, "max": 5, "step": 1},
            "b": {"type": "float", "min": 0.5, "max": 2.0, "step": 0.5},
        }
        assert count_combinations(space) == len(generate_combinations(space))
