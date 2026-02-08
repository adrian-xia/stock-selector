"""测试 StrategyFactory 注册、查询和实例化。"""

import pytest

from app.strategy.factory import STRATEGY_REGISTRY, StrategyFactory, StrategyMeta
from app.strategy.base import BaseStrategy


class TestStrategyRegistry:
    """测试策略注册表。"""

    def test_registry_has_12_strategies(self) -> None:
        """注册表应包含 12 种策略。"""
        assert len(STRATEGY_REGISTRY) == 12

    def test_8_technical_strategies(self) -> None:
        """应有 8 种技术面策略。"""
        technical = [m for m in STRATEGY_REGISTRY.values() if m.category == "technical"]
        assert len(technical) == 8

    def test_4_fundamental_strategies(self) -> None:
        """应有 4 种基本面策略。"""
        fundamental = [m for m in STRATEGY_REGISTRY.values() if m.category == "fundamental"]
        assert len(fundamental) == 4


class TestStrategyFactoryGetStrategy:
    """测试 get_strategy 实例化。"""

    def test_get_by_name(self) -> None:
        """按名称获取策略实例。"""
        s = StrategyFactory.get_strategy("ma-cross")
        assert isinstance(s, BaseStrategy)
        assert s.name == "ma-cross"

    def test_get_with_custom_params(self) -> None:
        """自定义参数传递。"""
        s = StrategyFactory.get_strategy("ma-cross", params={"fast": 10})
        assert s.params["fast"] == 10

    def test_get_unknown_raises(self) -> None:
        """未知策略名称抛出 KeyError。"""
        with pytest.raises(KeyError, match="未注册"):
            StrategyFactory.get_strategy("nonexistent")


class TestStrategyFactoryGetAll:
    """测试 get_all。"""

    def test_returns_all(self) -> None:
        result = StrategyFactory.get_all()
        assert len(result) == 12
        assert all(isinstance(m, StrategyMeta) for m in result)


class TestStrategyFactoryGetByCategory:
    """测试 get_by_category。"""

    def test_filter_technical(self) -> None:
        result = StrategyFactory.get_by_category("technical")
        assert len(result) == 8
        assert all(m.category == "technical" for m in result)

    def test_filter_fundamental(self) -> None:
        result = StrategyFactory.get_by_category("fundamental")
        assert len(result) == 4
        assert all(m.category == "fundamental" for m in result)

    def test_filter_empty_category(self) -> None:
        result = StrategyFactory.get_by_category("nonexistent")
        assert result == []


class TestStrategyFactoryGetMeta:
    """测试 get_meta。"""

    def test_get_meta(self) -> None:
        meta = StrategyFactory.get_meta("ma-cross")
        assert meta.name == "ma-cross"
        assert meta.display_name == "均线金叉"
        assert meta.category == "technical"

    def test_get_meta_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="未注册"):
            StrategyFactory.get_meta("nonexistent")
