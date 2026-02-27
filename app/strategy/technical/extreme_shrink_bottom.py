"""地量见底策略。

逻辑：极端缩量+低换手率，阶段性底部信号。
默认参数：extreme_ratio=0.3, max_turnover=1.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class ExtremeShrinkBottomStrategy(BaseStrategy):
    """地量见底策略：极端缩量 + 低换手率 + 非一字板。"""

    name = "extreme-shrink-bottom"
    display_name = "地量见底"
    category = "technical"
    description = "极端缩量+低换手率，阶段性底部信号"
    default_params = {"extreme_ratio": 0.3, "max_turnover": 1.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        extreme_ratio = self.params.get("extreme_ratio", 0.3)
        max_turnover = self.params.get("max_turnover", 1.0)

        high = df.get("high", pd.Series(dtype=float)).astype(float).fillna(0)
        low = df.get("low", pd.Series(dtype=float)).astype(float).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).astype(float).fillna(0)
        turnover_rate = df.get("turnover_rate", pd.Series(dtype=float)).astype(float).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).astype(float).fillna(0)

        extreme_shrink = vol_ratio < extreme_ratio
        low_turnover = turnover_rate < max_turnover
        not_doji = high > low
        not_limit_down = pct_chg > -9.5
        trading = vol > 0

        return extreme_shrink & low_turnover & not_doji & not_limit_down & trading
