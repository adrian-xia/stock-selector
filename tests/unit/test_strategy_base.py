"""测试 BaseStrategy 抽象基类。"""

from datetime import date

import pandas as pd
import pytest

from app.strategy.base import BaseStrategy


class DummyStrategy(BaseStrategy):
    """用于测试的具体策略实现。"""

    name = "dummy"
    display_name = "测试策略"
    category = "technical"
    description = "仅用于测试"
    default_params = {"threshold": 10, "window": 5}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        return pd.Series(True, index=df.index)


class TestBaseStrategyInit:
    """测试策略实例化和参数合并。"""

    def test_default_params(self) -> None:
        """无自定义参数时使用默认值。"""
        s = DummyStrategy()
        assert s.params == {"threshold": 10, "window": 5}

    def test_custom_params_override(self) -> None:
        """自定义参数覆盖默认值。"""
        s = DummyStrategy(params={"threshold": 20})
        assert s.params["threshold"] == 20
        assert s.params["window"] == 5  # 未覆盖的保持默认

    def test_custom_params_add_new(self) -> None:
        """自定义参数可以添加新键。"""
        s = DummyStrategy(params={"extra": 99})
        assert s.params["extra"] == 99
        assert s.params["threshold"] == 10

    def test_none_params(self) -> None:
        """params=None 等同于无参数。"""
        s = DummyStrategy(params=None)
        assert s.params == {"threshold": 10, "window": 5}

    def test_empty_params(self) -> None:
        """空字典不影响默认值。"""
        s = DummyStrategy(params={})
        assert s.params == {"threshold": 10, "window": 5}


class TestBaseStrategyAttributes:
    """测试策略类属性。"""

    def test_name(self) -> None:
        s = DummyStrategy()
        assert s.name == "dummy"

    def test_display_name(self) -> None:
        s = DummyStrategy()
        assert s.display_name == "测试策略"

    def test_category(self) -> None:
        s = DummyStrategy()
        assert s.category == "technical"

    def test_description(self) -> None:
        s = DummyStrategy()
        assert s.description == "仅用于测试"


class TestBaseStrategyAbstract:
    """测试抽象方法约束。"""

    def test_cannot_instantiate_base(self) -> None:
        """不能直接实例化 BaseStrategy。"""
        with pytest.raises(TypeError):
            BaseStrategy()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_filter_batch_returns_series(self) -> None:
        """filter_batch 返回布尔 Series。"""
        s = DummyStrategy()
        df = pd.DataFrame({"ts_code": ["000001.SZ", "000002.SZ"]})
        result = await s.filter_batch(df, date(2026, 2, 7))
        assert isinstance(result, pd.Series)
        assert len(result) == 2
        assert result.dtype == bool
