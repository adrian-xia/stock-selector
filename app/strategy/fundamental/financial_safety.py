"""财务安全策略。

逻辑：资产负债率 < 60%, 流动比率 > 1.5。
默认参数：debt_ratio_max=60, current_ratio_min=1.5
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class FinancialSafetyStrategy(BaseStrategy):
    """财务安全策略：低负债 + 高流动性。"""

    name = "financial-safety"
    display_name = "财务安全"
    category = "fundamental"
    description = "资产负债率低于60%，流动比率高于1.5"
    default_params = {"debt_ratio_max": 60, "current_ratio_min": 1.5}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选财务安全的股票。"""
        debt_max = self.params.get("debt_ratio_max", 60)
        current_min = self.params.get("current_ratio_min", 1.5)

        debt_ratio = df.get(
            "debt_ratio", pd.Series(dtype=float)
        ).fillna(100)
        current_ratio = df.get(
            "current_ratio", pd.Series(dtype=float)
        ).fillna(0)

        debt_ok = debt_ratio < debt_max
        liquidity_ok = current_ratio >= current_min

        return debt_ok & liquidity_ok
