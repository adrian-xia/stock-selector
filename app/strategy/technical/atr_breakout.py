"""ATR 波动率突破策略。

逻辑：价格突破 MA20 + ATR14 * 倍数。
默认参数：atr_multiplier=1.5
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class ATRBreakoutStrategy(BaseStrategy):
    """ATR 波动率突破策略：价格突破均线 + ATR 波动带。"""

    name = "atr-breakout"
    display_name = "ATR波动率突破"
    category = "technical"
    description = "价格突破 MA20 + ATR14 波动带上轨"
    default_params = {"atr_multiplier": 1.5}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 ATR 波动率突破信号。"""
        multiplier = self.params.get("atr_multiplier", 1.5)

        close = df.get("close", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        atr14 = df.get("atr14", pd.Series(dtype=float)).fillna(0)
        prev_close = df.get("close_prev", pd.Series(dtype=float)).fillna(0)
        prev_ma20 = df.get("ma20_prev", pd.Series(dtype=float)).fillna(0)
        prev_atr14 = df.get("atr14_prev", pd.Series(dtype=float)).fillna(0)

        # 突破：今日收盘 > MA20 + ATR * 倍数，且昨日未突破
        upper_band = ma20 + atr14 * multiplier
        prev_upper_band = prev_ma20 + prev_atr14 * multiplier
        breakout = (close > upper_band) & (prev_close <= prev_upper_band)

        # 指标有效
        valid = (ma20 > 0) & (atr14 > 0)

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return breakout & valid & trading
