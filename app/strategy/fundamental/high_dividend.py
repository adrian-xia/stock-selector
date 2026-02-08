"""高股息策略。

逻辑：股息率 > 3%, PE < 20。
默认参数：min_dividend_yield=3.0, pe_max=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class HighDividendStrategy(BaseStrategy):
    """高股息策略：高股息率 + 低估值。"""

    name = "high-dividend"
    display_name = "高股息"
    category = "fundamental"
    description = "股息率高于3%，市盈率低于20"
    default_params = {"min_dividend_yield": 3.0, "pe_max": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选高股息股票。"""
        min_yield = self.params.get("min_dividend_yield", 3.0)
        pe_max = self.params.get("pe_max", 20)

        dividend_yield = df.get(
            "dividend_yield", pd.Series(dtype=float)
        ).fillna(0)
        pe = df.get("pe_ttm", pd.Series(dtype=float)).fillna(-1)

        yield_ok = dividend_yield >= min_yield
        pe_ok = (pe > 0) & (pe < pe_max)

        return yield_ok & pe_ok
