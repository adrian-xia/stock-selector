"""净利润连续增长策略。

逻辑：利润同比增长率 >= 阈值。
默认参数：profit_growth_min=5.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class ProfitContinuousGrowthStrategy(BaseStrategy):
    """净利润连续增长策略：利润同比增长持续为正。"""

    name = "profit-continuous-growth"
    display_name = "净利润连续增长"
    category = "fundamental"
    description = "利润同比增长率持续为正，成长性好"
    default_params = {"profit_growth_min": 5.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选利润持续增长的股票。"""
        growth_min = self.params.get("profit_growth_min", 5.0)

        profit_yoy = df.get("profit_yoy", pd.Series(dtype=float)).fillna(-999)

        return profit_yoy >= growth_min
