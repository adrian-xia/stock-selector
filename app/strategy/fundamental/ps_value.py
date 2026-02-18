"""市销率低估值策略。

逻辑：PS_TTM > 0 且 PS_TTM < 阈值，适合高成长但尚未盈利的公司。
默认参数：ps_max=3.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class PSValueStrategy(BaseStrategy):
    """市销率低估值策略：PS_TTM 低于阈值。"""

    name = "ps-value"
    display_name = "市销率低估值"
    category = "fundamental"
    description = "市销率低于3倍，适合高成长公司"
    default_params = {"ps_max": 3.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选低市销率股票。"""
        ps_max = self.params.get("ps_max", 3.0)

        ps = df.get("ps_ttm", pd.Series(dtype=float)).fillna(-1)

        # PS > 0 且 PS < 阈值
        return (ps > 0) & (ps < ps_max)
