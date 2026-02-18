"""现金流质量策略。

逻辑：每股经营现金流 / 每股收益 >= 阈值，且 EPS > 0。
默认参数：ocf_eps_ratio_min=1.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class CashflowQualityStrategy(BaseStrategy):
    """现金流质量策略：经营现金流大于每股收益。"""

    name = "cashflow-quality"
    display_name = "现金流质量"
    category = "fundamental"
    description = "每股经营现金流大于每股收益，现金流质量高"
    default_params = {"ocf_eps_ratio_min": 1.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选现金流质量好的股票。"""
        ratio_min = self.params.get("ocf_eps_ratio_min", 1.0)

        ocf = df.get("ocf_per_share", pd.Series(dtype=float)).fillna(0)
        eps = df.get("eps", pd.Series(dtype=float)).fillna(0)

        # EPS > 0 且 OCF > 0 且 OCF/EPS >= 阈值
        eps_ok = eps > 0
        ocf_ok = ocf > 0
        ratio = pd.Series(0.0, index=df.index)
        valid = eps_ok & ocf_ok
        ratio[valid] = ocf[valid] / eps[valid]

        return valid & (ratio >= ratio_min)
