"""MACD 金叉策略。

逻辑：DIF 上穿 DEA。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class MACDGoldenStrategy(BaseStrategy):
    """MACD 金叉策略：DIF 上穿 DEA。"""

    name = "macd-golden"
    display_name = "MACD金叉"
    category = "technical"
    description = "MACD DIF 线上穿 DEA 线，发出买入信号"
    default_params = {}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 MACD 金叉信号。"""
        prev_dif = df.get("macd_dif_prev", pd.Series(dtype=float)).fillna(0)
        prev_dea = df.get("macd_dea_prev", pd.Series(dtype=float)).fillna(0)
        cur_dif = df.get("macd_dif", pd.Series(dtype=float)).fillna(0)
        cur_dea = df.get("macd_dea", pd.Series(dtype=float)).fillna(0)

        cross = (prev_dif <= prev_dea) & (cur_dif > cur_dea)
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return cross & trading
