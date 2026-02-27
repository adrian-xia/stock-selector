"""回调半分位策略。

逻辑：多头排列中小幅回调不超半分位，多头力量仍强。
默认参数：max_pullback_pct=3.0, max_vol_ratio=0.8
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class PullbackHalfRuleStrategy(BaseStrategy):
    """回调半分位策略：多头排列 + 小幅缩量回调 + 未跌破半分位。"""

    name = "pullback-half-rule"
    display_name = "回调半分位"
    category = "technical"
    description = "多头排列中小幅回调不超半分位，多头力量仍强"
    default_params = {"max_pullback_pct": 3.0, "max_vol_ratio": 0.8}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        max_pullback_pct = self.params.get("max_pullback_pct", 3.0)
        max_vol_ratio = self.params.get("max_vol_ratio", 0.8)

        close = df.get("close", pd.Series(dtype=float)).astype(float).fillna(0)
        ma5 = df.get("ma5", pd.Series(dtype=float)).astype(float).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).astype(float).fillna(0)
        ma60 = df.get("ma60", pd.Series(dtype=float)).astype(float).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).astype(float).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).astype(float).fillna(0)

        bull_arrange = (ma5 > ma20) & (ma20 > ma60) & (ma60 > 0)
        pullback = (pct_chg > -max_pullback_pct) & (pct_chg < 0)
        above_ma20 = close > ma20
        above_half = close > (ma5 + ma20) / 2
        shrink = vol_ratio < max_vol_ratio
        trading = vol > 0

        return bull_arrange & pullback & above_ma20 & above_half & shrink & trading
