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

    def calculate_style_strength(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """计算风格强度（0.0-1.0）。

        基于股息率和 PE 的归一化得分。
        """
        dividend_yield = df.get(
            "dividend_yield", pd.Series(dtype=float)
        ).fillna(0)
        pe = df.get("pe_ttm", pd.Series(dtype=float)).fillna(-1)

        # 股息率得分：越高越好，股息率 > 6% 得 1.0，股息率 < 1% 得 0.0
        yield_score = ((dividend_yield - 1) / 5).clip(0, 1)

        # PE 得分：越低越好，PE < 10 得 1.0，PE > 30 得 0.0
        pe_score = ((30 - pe.clip(0, 30)) / 20).clip(0, 1)
        pe_score = pe_score.where(pe > 0, 0)  # 亏损股票得 0 分

        # 综合得分：加权平均（股息率 60%，PE 40%）
        strength = (yield_score * 0.6 + pe_score * 0.4)

        return strength
