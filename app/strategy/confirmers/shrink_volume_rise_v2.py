"""Confirmer 策略：缩量上涨。

筹码锁定确认，为趋势延续信号 +0.2 加分。
返回加分系数 0.0-1.0。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, StrategyRole


class ShrinkVolumeRiseConfirmerV2(BaseStrategyV2):
    """缩量上涨 Confirmer：筹码锁定确认。"""

    name = "shrink-volume-rise-confirmer-v2"
    display_name = "缩量上涨（确认）"
    role = StrategyRole.CONFIRMER
    signal_group = None
    description = "上升趋势中缩量上涨，筹码锁定良好，为趋势延续信号加分"
    default_params = {
        "max_vol_ratio": 0.8,
        "min_pct_chg": 0.5,
    }
    ai_rating = 6.87  # 三模型均分（从 trigger 降级为 confirmer）

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> pd.Series:
        """执行确认检查。

        Returns:
            pd.Series[float]，加分系数 0.0-1.0
        """
        max_vol_ratio = self.params.get("max_vol_ratio", 0.8)
        min_pct_chg = self.params.get("min_pct_chg", 0.5)

        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).fillna(0)
        vol_ma5 = df.get("vol_ma5", pd.Series(dtype=float)).fillna(1)

        # 上升趋势：MA5 > MA20
        ma5 = df.get("ma5", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        uptrend = (ma5 > ma20) & (ma20 > 0)

        # 缩量上涨
        vol_ratio = vol / vol_ma5
        shrink_rise = (
            uptrend
            & (pct_chg >= min_pct_chg)  # 上涨
            & (vol_ratio <= max_vol_ratio)  # 缩量
            & (vol > 0)
        )

        return shrink_rise.astype(float)
