"""PEG 估值策略。

逻辑：PEG = PE_TTM / profit_yoy < 阈值，PE 和利润增长率均须为正。
默认参数：peg_max=1.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class PEGValueStrategy(BaseStrategy):
    """PEG 估值策略：成长性被低估的股票。"""

    name = "peg-value"
    display_name = "PEG估值"
    category = "fundamental"
    description = "PEG低于1，成长性被低估"
    default_params = {"peg_max": 1.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选低 PEG 股票。"""
        peg_max = self.params.get("peg_max", 1.0)

        pe = df.get("pe_ttm", pd.Series(dtype=float)).fillna(-1)
        profit_yoy = df.get("profit_yoy", pd.Series(dtype=float)).fillna(-1)

        # PE > 0 且利润增长 > 0 时才计算 PEG
        valid = (pe > 0) & (profit_yoy > 0)
        peg = pd.Series(float("inf"), index=df.index)
        peg[valid] = pe[valid] / profit_yoy[valid]

        return valid & (peg < peg_max)
