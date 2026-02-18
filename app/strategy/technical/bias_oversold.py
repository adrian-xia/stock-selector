"""BIAS 乖离率策略。

逻辑：BIAS 达到超卖极值，预期均值回归。
默认参数：oversold_bias=-6.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class BIASStrategy(BaseStrategy):
    """BIAS 乖离率策略：价格偏离 MA20 达到超卖极值。"""

    name = "bias-oversold"
    display_name = "BIAS乖离率"
    category = "technical"
    description = "BIAS 乖离率达到超卖极值（<-6%），预期均值回归"
    default_params = {"oversold_bias": -6.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 BIAS 超卖信号。"""
        oversold_bias = self.params.get("oversold_bias", -6.0)

        bias = df.get("bias", pd.Series(dtype=float)).fillna(0)

        # 超卖：BIAS <= 阈值
        signal = bias <= oversold_bias

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return signal & trading
