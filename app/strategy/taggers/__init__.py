"""V2 Tagger 策略：风格标签。

Tagger 输出 dict[str, pd.Series[float]]，风格强度 0.0-1.0。
用于 Layer 1 为股票打风格标签（成长/价值/红利等）。
"""

from app.strategy.adapters.tagger_adapter import TaggerAdapter
from app.strategy.base import BaseStrategyV2
from app.strategy.fundamental.high_dividend import HighDividendStrategy
from app.strategy.fundamental.low_pe_high_roe import LowPEHighROEStrategy


class LowPEHighROETaggerV2(BaseStrategyV2):
    """低估值高成长 Tagger V2。"""

    def __init__(self, params: dict | None = None) -> None:
        """初始化 Tagger。"""
        self._adapter = TaggerAdapter(
            LowPEHighROEStrategy(params),
            style_key="growth",
            ai_rating=7.13,
        )
        # 复制适配器的属性
        self.name = self._adapter.name
        self.display_name = self._adapter.display_name
        self.role = self._adapter.role
        self.signal_group = self._adapter.signal_group
        self.description = self._adapter.description
        self.default_params = self._adapter.default_params
        self.ai_rating = self._adapter.ai_rating
        self.params = self._adapter.params

    async def execute(self, df, target_date):
        """执行 Tagger 策略。"""
        return await self._adapter.execute(df, target_date)


class HighDividendTaggerV2(BaseStrategyV2):
    """高股息 Tagger V2。"""

    def __init__(self, params: dict | None = None) -> None:
        """初始化 Tagger。"""
        self._adapter = TaggerAdapter(
            HighDividendStrategy(params),
            style_key="dividend",
            ai_rating=6.47,
        )
        # 复制适配器的属性
        self.name = self._adapter.name
        self.display_name = self._adapter.display_name
        self.role = self._adapter.role
        self.signal_group = self._adapter.signal_group
        self.description = self._adapter.description
        self.default_params = self._adapter.default_params
        self.ai_rating = self._adapter.ai_rating
        self.params = self._adapter.params

    async def execute(self, df, target_date):
        """执行 Tagger 策略。"""
        return await self._adapter.execute(df, target_date)


__all__ = [
    "LowPEHighROETaggerV2",
    "HighDividendTaggerV2",
]
