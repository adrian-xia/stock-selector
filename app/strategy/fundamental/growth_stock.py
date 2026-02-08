"""成长股策略。

逻辑：营收增长 > 20%, 利润增长 > 20%。
默认参数：revenue_growth_min=20, profit_growth_min=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class GrowthStockStrategy(BaseStrategy):
    """成长股策略：高营收增长 + 高利润增长。"""

    name = "growth-stock"
    display_name = "成长股"
    category = "fundamental"
    description = "营收和利润同比增长均超过20%"
    default_params = {"revenue_growth_min": 20, "profit_growth_min": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选高成长股票。"""
        rev_min = self.params.get("revenue_growth_min", 20)
        profit_min = self.params.get("profit_growth_min", 20)

        revenue_yoy = df.get(
            "revenue_yoy", pd.Series(dtype=float)
        ).fillna(0)
        profit_yoy = df.get(
            "profit_yoy", pd.Series(dtype=float)
        ).fillna(0)

        return (revenue_yoy >= rev_min) & (profit_yoy >= profit_min)
