"""Tagger 适配器：将 V1 BaseStrategy 适配为 V2 Tagger 角色。

Tagger 策略返回 dict[str, pd.Series[float]]，键为风格标签，值为强度 Series（0.0-1.0）。
可以复用 V1 的 filter_batch 方法，将 bool 转换为 1.0/0.0 强度。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy, BaseStrategyV2, StrategyRole


class TaggerAdapter(BaseStrategyV2):
    """Tagger 适配器：包装 V1 策略为 V2 Tagger。

    使用方式：
        v1_strategy = LowPEHighROEStrategy()
        v2_tagger = TaggerAdapter(
            v1_strategy,
            style_key="growth",
            ai_rating=7.62
        )
    """

    def __init__(
        self,
        v1_strategy: BaseStrategy,
        style_key: str,
        ai_rating: float = 5.0,
    ) -> None:
        """初始化适配器。

        Args:
            v1_strategy: V1 策略实例
            style_key: 风格标签键（如 "growth", "dividend"）
            ai_rating: 三模型综合均分
        """
        self.v1_strategy = v1_strategy
        self.style_key = style_key
        self.name = v1_strategy.name
        self.display_name = v1_strategy.display_name
        self.role = StrategyRole.TAGGER
        self.signal_group = None
        self.description = v1_strategy.description
        self.default_params = v1_strategy.default_params
        self.ai_rating = ai_rating
        self.params = v1_strategy.params

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> dict[str, pd.Series]:
        """执行 Tagger 策略。

        Returns:
            dict[str, pd.Series[float]]，键为风格标签，值为强度 Series（0.0-1.0）
            V1 策略返回 bool，转换为 1.0（命中）或 0.0（未命中）
        """
        mask = await self.v1_strategy.filter_batch(df, target_date)
        # 将 bool 转换为 float：True -> 1.0, False -> 0.0
        strength = mask.astype(float)
        return {self.style_key: strength}
