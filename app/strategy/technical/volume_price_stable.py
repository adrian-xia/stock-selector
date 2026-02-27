"""量缩价稳策略。

逻辑：量缩价稳，抛压耗尽的底部企稳信号。
默认参数：max_vol_ratio=0.5, max_pct_chg=2.0, ma_position=1.02
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class VolumePriceStableStrategy(BaseStrategy):
    """量缩价稳策略：缩量 + 价格企稳 + 经历调整。"""

    name = "volume-price-stable"
    display_name = "量缩价稳"
    category = "technical"
    description = "量缩价稳，抛压耗尽的底部企稳信号"
    default_params = {"max_vol_ratio": 0.5, "max_pct_chg": 2.0, "ma_position": 1.02}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        max_vol_ratio = self.params.get("max_vol_ratio", 0.5)
        max_pct_chg = self.params.get("max_pct_chg", 2.0)
        ma_position = self.params.get("ma_position", 1.02)

        close = df.get("close", pd.Series(dtype=float)).astype(float).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).astype(float).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).astype(float).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).astype(float).fillna(0)

        shrink = vol_ratio < max_vol_ratio
        stable = pct_chg.abs() < max_pct_chg
        adjusted = (ma20 > 0) & (close <= ma20 * ma_position)
        not_limit_down = pct_chg > -9.5
        trading = vol > 0

        return shrink & stable & adjusted & not_limit_down & trading
