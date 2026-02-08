"""低估值高成长策略。

逻辑：PE < 30, ROE > 15%, 利润增长 > 20%。
默认参数：pe_max=30, roe_min=15, profit_growth_min=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class LowPEHighROEStrategy(BaseStrategy):
    """低估值高成长策略：低 PE + 高 ROE + 利润增长。"""

    name = "low-pe-high-roe"
    display_name = "低估值高成长"
    category = "fundamental"
    description = "市盈率低于30，ROE高于15%，利润同比增长超20%"
    default_params = {"pe_max": 30, "roe_min": 15, "profit_growth_min": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选低估值高成长股票。"""
        pe_max = self.params.get("pe_max", 30)
        roe_min = self.params.get("roe_min", 15)
        profit_growth_min = self.params.get("profit_growth_min", 20)

        pe = df.get("pe_ttm", pd.Series(dtype=float)).fillna(-1)
        roe = df.get("roe", pd.Series(dtype=float)).fillna(0)
        profit_yoy = df.get("profit_yoy", pd.Series(dtype=float)).fillna(0)

        # PE > 0（排除亏损）且 PE < 阈值
        pe_ok = (pe > 0) & (pe < pe_max)
        roe_ok = roe >= roe_min
        growth_ok = profit_yoy >= profit_growth_min

        return pe_ok & roe_ok & growth_ok
