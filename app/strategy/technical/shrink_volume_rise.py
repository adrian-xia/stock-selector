"""缩量上涨策略。

逻辑：上升趋势中缩量上涨，筹码锁定良好。
默认参数：max_vol_ratio=0.8, min_pct_chg=0.5
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class ShrinkVolumeRiseStrategy(BaseStrategy):
    """缩量上涨策略：上升趋势 + 缩量 + 收阳。"""

    name = "shrink-volume-rise"
    display_name = "缩量上涨"
    category = "technical"
    description = "上升趋势中缩量上涨，筹码锁定良好"
    default_params = {"max_vol_ratio": 0.8, "min_pct_chg": 0.5}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        max_vol_ratio = self.params.get("max_vol_ratio", 0.8)
        min_pct_chg = self.params.get("min_pct_chg", 0.5)

        close = df.get("close", pd.Series(dtype=float)).astype(float).fillna(0)
        open_ = df.get("open", pd.Series(dtype=float)).astype(float).fillna(0)
        ma5 = df.get("ma5", pd.Series(dtype=float)).astype(float).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).astype(float).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).astype(float).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).astype(float).fillna(0)

        uptrend = (close > ma20) & (ma5 > ma20)
        bullish = close > open_
        gain = pct_chg >= min_pct_chg
        shrink = vol_ratio < max_vol_ratio
        trading = vol > 0

        return uptrend & bullish & gain & shrink & trading
