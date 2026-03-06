"""低估值高成长策略。

逻辑：PE < 30, ROE > 15%, 利润增长 > 20%。
默认参数：pe_max=30, roe_min=15, profit_growth_min=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class LowPEHighROEStrategy(BaseStrategy):
    """低估值高成长策略：低 PE + 高 ROE + 利润增长。"""

    name = "low-pe-high-roe"
    display_name = "低估值高成长"
    category = "fundamental"
    description = "市盈率低于30，ROE高于15%，利润同比增长超20%"
    default_params = {"pe_max": 30, "roe_min": 15, "profit_growth_min": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选低估值高成长股票。"""
        pe_max = self.params.get("pe_max", 30)
        roe_min = self.params.get("roe_min", 15)
        profit_growth_min = self.params.get("profit_growth_min", 20)

        pe = df.get("pe_ttm", pd.Series(dtype=float)).fillna(-1)
        roe = df.get("roe", pd.Series(dtype=float)).fillna(0)
        profit_yoy = df.get("profit_yoy", pd.Series(dtype=float)).fillna(0)

        # PE > 0（排除亏损）且 PE < 阈值
        pe_ok = (pe > 0) & (pe < pe_max)
        roe_ok = roe >= roe_min
        growth_ok = profit_yoy >= profit_growth_min

        return pe_ok & roe_ok & growth_ok

    def calculate_style_strength(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """计算风格强度（0.0-1.0）。

        基于 PE、ROE、profit_yoy 的归一化得分。
        """
        pe = df.get("pe_ttm", pd.Series(dtype=float)).fillna(-1)
        roe = df.get("roe", pd.Series(dtype=float)).fillna(0)
        profit_yoy = df.get("profit_yoy", pd.Series(dtype=float)).fillna(0)

        # PE 得分：越低越好，PE < 10 得 1.0，PE > 50 得 0.0
        pe_score = ((50 - pe.clip(0, 50)) / 40).clip(0, 1)
        pe_score = pe_score.where(pe > 0, 0)  # 亏损股票得 0 分

        # ROE 得分：越高越好，ROE > 30% 得 1.0，ROE < 5% 得 0.0
        roe_score = ((roe - 5) / 25).clip(0, 1)

        # 利润增长得分：越高越好，增长 > 50% 得 1.0，增长 < 0% 得 0.0
        growth_score = (profit_yoy / 50).clip(0, 1)

        # 综合得分：加权平均（PE 40%，ROE 30%，增长 30%）
        strength = (pe_score * 0.4 + roe_score * 0.3 + growth_score * 0.3)

        return strength
