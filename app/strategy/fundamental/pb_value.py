"""PB 低估值策略。

逻辑：PB > 0 且 PB < 阈值，适合重资产行业价值投资。
默认参数：pb_max=2.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class PBValueStrategy(BaseStrategy):
    """PB 低估值策略：市净率低于阈值。"""

    name = "pb-value"
    display_name = "PB低估值"
    category = "fundamental"
    description = "市净率低于2倍，适合重资产行业价值投资"
    default_params = {"pb_max": 2.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选低 PB 股票。"""
        pb_max = self.params.get("pb_max", 2.0)

        pb = df.get("pb", pd.Series(dtype=float)).fillna(-1)

        # PB > 0（排除负净资产）且 PB < 阈值
        return (pb > 0) & (pb < pb_max)
