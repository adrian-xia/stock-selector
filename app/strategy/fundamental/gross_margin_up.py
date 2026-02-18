"""毛利率提升策略。

逻辑：毛利率 >= 阈值，筛选盈利能力强的公司。
默认参数：gross_margin_min=30.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class GrossMarginUpStrategy(BaseStrategy):
    """毛利率提升策略：毛利率高于阈值。"""

    name = "gross-margin-up"
    display_name = "毛利率提升"
    category = "fundamental"
    description = "毛利率高于30%，盈利能力强"
    default_params = {"gross_margin_min": 30.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选高毛利率股票。"""
        gross_margin_min = self.params.get("gross_margin_min", 30.0)

        gross_margin = df.get("gross_margin", pd.Series(dtype=float)).fillna(0)

        return gross_margin >= gross_margin_min
