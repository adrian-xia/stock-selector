"""综合质量评分策略 V2：Scorer 角色。

V2 改进：
1. 返回连续分数（0-100），不再是 bool
2. 新增毛利率边际变化维度（合并 #31）
3. 行业中性化 Z-Score 打分（TODO: Phase 2 后期实现）
4. 权重按滚动 IC/IR 自适应（TODO: Phase 4 实现）

当前实现：五因子加权评分（ROE 25% + 成长 20% + 安全 20% + 估值 20% + 毛利率 15%）
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, StrategyRole


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


def _score_gross_margin(gross_margin: pd.Series) -> pd.Series:
    """毛利率评分：>= 50 → 100, >= 40 → 80, >= 30 → 60, >= 20 → 40, 否则 20。"""
    score = pd.Series(20.0, index=gross_margin.index)
    score[gross_margin >= 20] = 40.0
    score[gross_margin >= 30] = 60.0
    score[gross_margin >= 40] = 80.0
    score[gross_margin >= 50] = 100.0
    return score


class QualityScoreStrategyV2(BaseStrategyV2):
    """综合质量评分策略 V2：Scorer 角色。"""

    name = "quality-score-v2"
    display_name = "综合质量评分"
    role = StrategyRole.SCORER
    signal_group = None
    description = "ROE+成长+安全+估值+毛利率五因子加权评分（0-100 连续分数）"
    default_params = {}
    ai_rating = 7.80  # 三模型均分

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> pd.Series:
        """执行质量评分。

        Returns:
            pd.Series[float]，0-100 连续分数，数据缺失返回 0
        """
        roe = df.get("roe", pd.Series(dtype=float))
        profit_yoy = df.get("profit_yoy", pd.Series(dtype=float))
        debt_ratio = df.get("debt_ratio", pd.Series(dtype=float))
        pe_ttm = df.get("pe_ttm", pd.Series(dtype=float))
        gross_margin = df.get("gross_margin", pd.Series(dtype=float))

        # 任一关键指标缺失或 PE <= 0（亏损股）则评分为 0
        has_data = (
            roe.notna()
            & profit_yoy.notna()
            & debt_ratio.notna()
            & pe_ttm.notna()
            & gross_margin.notna()
            & (pe_ttm > 0)
        )

        # 填充 NaN 为默认低分值（仅用于计算，has_data 已过滤）
        roe_filled = roe.fillna(0)
        growth_filled = profit_yoy.fillna(-999)
        safety_filled = debt_ratio.fillna(100)
        pe_filled = pe_ttm.fillna(999)
        margin_filled = gross_margin.fillna(0)

        # 计算各维度评分（五因子）
        total = (
            _score_roe(roe_filled) * 0.25
            + _score_growth(growth_filled) * 0.20
            + _score_safety(safety_filled) * 0.20
            + _score_valuation(pe_filled) * 0.20
            + _score_gross_margin(margin_filled) * 0.15
        )

        # 数据缺失的股票评分为 0
        total[~has_data] = 0.0

        return total
