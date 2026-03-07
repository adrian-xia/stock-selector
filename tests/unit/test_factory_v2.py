"""测试 V2 策略工厂。"""

from app.strategy.base import StrategyRole
from app.strategy.factory import StrategyFactoryV2


class TestStrategyFactoryV2:
    """测试 V2 工厂注册与实例化。"""

    def test_registry_has_20_v2_strategies(self) -> None:
        """V2 注册表应包含 20 个策略。"""
        assert len(StrategyFactoryV2.get_all()) == 20

    def test_get_trigger_strategy_overrides_meta(self) -> None:
        """实例化后应以注册表元数据为准。"""
        strategy = StrategyFactoryV2.get_strategy("volume-contraction-pullback-trigger-v2")
        assert strategy.name == "volume-contraction-pullback-trigger-v2"
        assert strategy.ai_rating == 7.42
        assert strategy.role == StrategyRole.TRIGGER
        assert strategy.params["max_vol_ratio"] == 0.6

