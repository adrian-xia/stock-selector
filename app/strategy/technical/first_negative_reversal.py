"""首阴反包策略。

逻辑：强势股首阴后阳线反包，多头重新占优。
默认参数：min_pct_chg=2.0, min_vol_ratio=1.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class FirstNegativeReversalStrategy(BaseStrategy):
    """首阴反包策略：前日收阴 + 今日阳线反包。"""

    name = "first-negative-reversal"
    display_name = "首阴反包"
    category = "technical"
    description = "强势股首阴后阳线反包，多头重新占优"
    default_params = {"min_pct_chg": 2.0, "min_vol_ratio": 1.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        min_pct_chg = self.params.get("min_pct_chg", 2.0)
        min_vol_ratio = self.params.get("min_vol_ratio", 1.0)

        close = df.get("close", pd.Series(dtype=float)).astype(float).fillna(0)
        open_ = df.get("open", pd.Series(dtype=float)).astype(float).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).astype(float).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).astype(float).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).astype(float).fillna(0)
        close_prev = df.get("close_prev", pd.Series(dtype=float)).astype(float).fillna(0)

        # 前日收阴：优先用 open_prev，否则用 pct_chg_prev 近似
        if "open_prev" in df.columns:
            open_prev = df["open_prev"].astype(float).fillna(0)
            prev_negative = (close_prev > 0) & (close_prev < open_prev)
        elif "pct_chg_prev" in df.columns:
            pct_chg_prev = df["pct_chg_prev"].astype(float).fillna(0)
            prev_negative = pct_chg_prev < 0
        else:
            # 无前日数据，条件宽松处理
            prev_negative = pd.Series(True, index=df.index)

        uptrend = (close > ma20) & (ma20 > 0)
        bullish_today = (close > open_) & (pct_chg >= min_pct_chg)
        reversal = (close_prev > 0) & (close > close_prev)
        volume_ok = vol_ratio >= min_vol_ratio
        trading = vol > 0

        return uptrend & prev_negative & bullish_today & reversal & volume_ok & trading
