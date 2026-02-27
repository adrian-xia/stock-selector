"""后量超前量策略。

逻辑：资金加速流入，量能持续放大的趋势加速信号。
默认参数：surge_ratio=2.0, vol_ma_ratio=1.2, min_pct_chg=1.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class VolumeSurgeContinuationStrategy(BaseStrategy):
    """后量超前量策略：今日放量 + 量能持续放大 + 上升趋势。"""

    name = "volume-surge-continuation"
    display_name = "后量超前量"
    category = "technical"
    description = "资金加速流入，量能持续放大的趋势加速信号"
    default_params = {"surge_ratio": 2.0, "vol_ma_ratio": 1.2, "min_pct_chg": 1.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        surge_ratio = self.params.get("surge_ratio", 2.0)
        vol_ma_ratio = self.params.get("vol_ma_ratio", 1.2)
        min_pct_chg = self.params.get("min_pct_chg", 1.0)

        ma5 = df.get("ma5", pd.Series(dtype=float)).astype(float).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).astype(float).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ma5 = df.get("vol_ma5", pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ma10 = df.get("vol_ma10", pd.Series(dtype=float)).astype(float).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).astype(float).fillna(0)

        surge = vol_ratio >= surge_ratio
        # 后量超前量：vol_ma5 / vol_ma10 >= vol_ma_ratio，避免除零
        vol_acceleration = (vol_ma10 > 0) & (vol_ma5 / vol_ma10.replace(0, float("nan")).fillna(1) >= vol_ma_ratio)
        gain = pct_chg >= min_pct_chg
        uptrend = (ma5 > ma20) & (ma20 > 0)
        trading = vol > 0

        return surge & vol_acceleration & gain & uptrend & trading
