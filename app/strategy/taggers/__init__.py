"""V2 Tagger 策略：风格标签。

Tagger 输出 dict[str, pd.Series[float]]，风格强度 0.0-1.0。
用于 Layer 1 为股票打风格标签（成长/价值/红利等）。
"""

from app.strategy.adapters.tagger_adapter import TaggerAdapter
from app.strategy.base import BaseStrategyV2, StrategyRole
from app.strategy.fundamental.high_dividend import HighDividendStrategy
from app.strategy.fundamental.low_pe_high_roe import LowPEHighROEStrategy


class LowPEHighROETaggerV2(BaseStrategyV2):
    """低估值高成长 Tagger V2。"""

    name = "low-pe-high-roe-tagger-v2"
    display_name = "低估值高成长（标签）"
    role = StrategyRole.TAGGER
    signal_group = None
    description = "PE<30 + ROE>=15% + 利润增速>=20%"
    default_params = LowPEHighROEStrategy.default_params
    ai_rating = 7.62

    def __init__(self, params: dict | None = None) -> None:
        """初始化 Tagger。"""
        super().__init__(params)
        self._adapter = TaggerAdapter(
            LowPEHighROEStrategy(self.params),
            style_key="growth",
            ai_rating=self.ai_rating,
        )

    async def execute(self, df, target_date):
        """执行 Tagger 策略。"""
        return await self._adapter.execute(df, target_date)


class HighDividendTaggerV2(BaseStrategyV2):
    """高股息 Tagger V2。"""

    name = "high-dividend-tagger-v2"
    display_name = "高股息（标签）"
    role = StrategyRole.TAGGER
    signal_group = None
    description = "股息率>=3% + PE<20"
    default_params = HighDividendStrategy.default_params
    ai_rating = 8.08

    def __init__(self, params: dict | None = None) -> None:
        """初始化 Tagger。"""
        super().__init__(params)
        self._adapter = TaggerAdapter(
            HighDividendStrategy(self.params),
            style_key="dividend",
            ai_rating=self.ai_rating,
        )

    async def execute(self, df, target_date):
        """执行 Tagger 策略。"""
        return await self._adapter.execute(df, target_date)


__all__ = [
    "LowPEHighROETaggerV2",
    "HighDividendTaggerV2",
]
