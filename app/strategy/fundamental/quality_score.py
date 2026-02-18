"""综合质量评分策略。

逻辑：多因子加权评分（ROE 30% + 成长 25% + 安全 25% + 估值 20%），总分 >= 阈值。
默认参数：score_min=60.0
"""

from datetime import date

import numpy as np
import pandas as pd

from app.strategy.base import BaseStrategy


def _score_roe(roe: pd.Series) -> pd.Series:
    """ROE 评分：>= 20 → 100, >= 15 → 80, >= 10 → 60, >= 5 → 40, 否则 20。"""
    score = pd.Series(20.0, index=roe.index)
    score[roe >= 5] = 40.0
    score[roe >= 10] = 60.0
    score[roe >= 15] = 80.0
    score[roe >= 20] = 100.0
    return score


def _score_growth(profit_yoy: pd.Series) -> pd.Series:
    """成长评分：>= 30 → 100, >= 20 → 80, >= 10 → 60, >= 0 → 40, 否则 20。"""
    score = pd.Series(20.0, index=profit_yoy.index)
    score[profit_yoy >= 0] = 40.0
    score[profit_yoy >= 10] = 60.0
    score[profit_yoy >= 20] = 80.0
    score[profit_yoy >= 30] = 100.0
    return score


def _score_safety(debt_ratio: pd.Series) -> pd.Series:
    """安全评分：<= 30 → 100, <= 40 → 80, <= 50 → 60, <= 60 → 40, 否则 20。"""
    score = pd.Series(20.0, index=debt_ratio.index)
    score[debt_ratio <= 60] = 40.0
    score[debt_ratio <= 50] = 60.0
    score[debt_ratio <= 40] = 80.0
    score[debt_ratio <= 30] = 100.0
    return score


def _score_valuation(pe_ttm: pd.Series) -> pd.Series:
    """估值评分：<= 10 → 100, <= 15 → 80, <= 20 → 60, <= 30 → 40, 否则 20。"""
    score = pd.Series(20.0, index=pe_ttm.index)
    score[pe_ttm <= 30] = 40.0
    score[pe_ttm <= 20] = 60.0
    score[pe_ttm <= 15] = 80.0
    score[pe_ttm <= 10] = 100.0
    return score


class QualityScoreStrategy(BaseStrategy):
    """综合质量评分策略：多因子加权评分。"""

    name = "quality-score"
    display_name = "综合质量评分"
    category = "fundamental"
    description = "ROE+成长+安全+估值多因子加权评分"
    default_params = {"score_min": 60.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """筛选综合质量评分达标的股票。"""
        score_min = self.params.get("score_min", 60.0)

        roe = df.get("roe", pd.Series(dtype=float))
        profit_yoy = df.get("profit_yoy", pd.Series(dtype=float))
        debt_ratio = df.get("debt_ratio", pd.Series(dtype=float))
        pe_ttm = df.get("pe_ttm", pd.Series(dtype=float))

        # 任一关键指标缺失则不评分
        has_data = roe.notna() & profit_yoy.notna() & debt_ratio.notna() & pe_ttm.notna()
        # PE 必须为正（排除亏损股）
        has_data = has_data & (pe_ttm > 0)

        # 填充 NaN 为默认低分值（仅用于计算，has_data 已过滤）
        roe_filled = roe.fillna(0)
        growth_filled = profit_yoy.fillna(-999)
        safety_filled = debt_ratio.fillna(100)
        pe_filled = pe_ttm.fillna(999)

        # 计算各维度评分
        total = (
            _score_roe(roe_filled) * 0.30
            + _score_growth(growth_filled) * 0.25
            + _score_safety(safety_filled) * 0.25
            + _score_valuation(pe_filled) * 0.20
        )

        return has_data & (total >= score_min)
