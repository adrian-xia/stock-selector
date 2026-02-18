"""经营现金流覆盖策略。

逻辑：每股经营现金流 >= 阈值 且 流动比率 >= 阈值。
默认参数：ocf_min=0.5, current_ratio_min=1.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class CashflowCoverageStrategy(BaseStrategy):
    """经营现金流覆盖策略：现金流能覆盖短期负债。"""

    name = "cashflow-coverage"
    display_name = "经营现金流覆盖"
    category = "fundamental"
    description = "经营现金流充裕且流动比率达标"
    default_params = {"ocf_min": 0.5, "current_ratio_min": 1.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选现金流覆盖充足的股票。"""
        ocf_min = self.params.get("ocf_min", 0.5)
        cr_min = self.params.get("current_ratio_min", 1.0)

        ocf = df.get("ocf_per_share", pd.Series(dtype=float)).fillna(0)
        cr = df.get("current_ratio", pd.Series(dtype=float)).fillna(0)

        return (ocf >= ocf_min) & (cr >= cr_min)
