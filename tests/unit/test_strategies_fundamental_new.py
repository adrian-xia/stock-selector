"""新增 8 种基本面策略的单元测试。

覆盖：
- 估值类：PBValueStrategy、PEGValueStrategy、PSValueStrategy
- 盈利类：GrossMarginUpStrategy、CashflowQualityStrategy、ProfitContinuousGrowthStrategy
- 安全类：CashflowCoverageStrategy
- 综合类：QualityScoreStrategy
- 策略工厂：注册表验证
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.strategy.fundamental.pb_value import PBValueStrategy
from app.strategy.fundamental.peg_value import PEGValueStrategy
from app.strategy.fundamental.ps_value import PSValueStrategy
from app.strategy.fundamental.gross_margin_up import GrossMarginUpStrategy
from app.strategy.fundamental.cashflow_quality import CashflowQualityStrategy
from app.strategy.fundamental.profit_continuous_growth import ProfitContinuousGrowthStrategy
from app.strategy.fundamental.cashflow_coverage import CashflowCoverageStrategy
from app.strategy.fundamental.quality_score import QualityScoreStrategy
from app.strategy.factory import STRATEGY_REGISTRY, StrategyFactory

TARGET_DATE = date(2026, 2, 18)


def _base_row(**overrides) -> dict:
    """构造单行基本面测试数据，默认值为"不触发"状态。"""
    row = {
        "ts_code": "000001.SZ",
        "close": 10.0,
        # 估值指标
        "pe_ttm": 25.0,
        "pb": 3.0,
        "ps_ttm": 5.0,
        "dividend_yield": 1.0,
        # 盈利指标
        "roe": 8.0,
        "eps": 1.0,
        "ocf_per_share": 0.5,
        "gross_margin": 20.0,
        "net_margin": 10.0,
        # 成长指标
        "revenue_yoy": 10.0,
        "profit_yoy": 10.0,
        # 安全指标
        "current_ratio": 1.2,
        "quick_ratio": 0.8,
        "debt_ratio": 55.0,
    }
    row.update(overrides)
    return row


def _make_df(*rows) -> pd.DataFrame:
    """从多行字典构造 DataFrame。"""
    return pd.DataFrame(rows)


# ============================================================
# PB 低估值策略
# ============================================================


class TestPBValueStrategy:
    """PB 低估值策略测试。"""

    async def test_hit_low_pb(self) -> None:
        """PB 低于阈值且为正值时命中。"""
        df = _make_df(_base_row(pb=1.5))
        s = PBValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert mask.iloc[0] is True or mask.iloc[0] == True  # noqa: E712

    async def test_miss_high_pb(self) -> None:
        """PB 超过阈值时不命中。"""
        df = _make_df(_base_row(pb=3.0))
        s = PBValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_negative_pb(self) -> None:
        """PB 为负值时不命中。"""
        df = _make_df(_base_row(pb=-0.5))
        s = PBValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_nan_pb(self) -> None:
        """PB 为 NaN 时不命中。"""
        df = _make_df(_base_row(pb=np.nan))
        s = PBValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]


# ============================================================
# PEG 估值策略
# ============================================================


class TestPEGValueStrategy:
    """PEG 估值策略测试。"""

    async def test_hit_low_peg(self) -> None:
        """PEG < 1 时命中。"""
        df = _make_df(_base_row(pe_ttm=15.0, profit_yoy=25.0))  # PEG = 0.6
        s = PEGValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert mask.iloc[0]

    async def test_miss_high_peg(self) -> None:
        """PEG > 1 时不命中。"""
        df = _make_df(_base_row(pe_ttm=30.0, profit_yoy=10.0))  # PEG = 3.0
        s = PEGValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_negative_profit(self) -> None:
        """利润负增长时不命中。"""
        df = _make_df(_base_row(pe_ttm=15.0, profit_yoy=-10.0))
        s = PEGValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_negative_pe(self) -> None:
        """PE 为负时不命中。"""
        df = _make_df(_base_row(pe_ttm=-5.0, profit_yoy=20.0))
        s = PEGValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]


# ============================================================
# 市销率低估值策略
# ============================================================


class TestPSValueStrategy:
    """市销率低估值策略测试。"""

    async def test_hit_low_ps(self) -> None:
        df = _make_df(_base_row(ps_ttm=2.0))
        s = PSValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert mask.iloc[0]

    async def test_miss_high_ps(self) -> None:
        df = _make_df(_base_row(ps_ttm=5.0))
        s = PSValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_nan_ps(self) -> None:
        df = _make_df(_base_row(ps_ttm=np.nan))
        s = PSValueStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]


# ============================================================
# 毛利率提升策略
# ============================================================


class TestGrossMarginUpStrategy:
    """毛利率提升策略测试。"""

    async def test_hit_high_margin(self) -> None:
        df = _make_df(_base_row(gross_margin=45.0))
        s = GrossMarginUpStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert mask.iloc[0]

    async def test_miss_low_margin(self) -> None:
        df = _make_df(_base_row(gross_margin=20.0))
        s = GrossMarginUpStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_nan_margin(self) -> None:
        df = _make_df(_base_row(gross_margin=np.nan))
        s = GrossMarginUpStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]


# ============================================================
# 现金流质量策略
# ============================================================


class TestCashflowQualityStrategy:
    """现金流质量策略测试。"""

    async def test_hit_good_cashflow(self) -> None:
        df = _make_df(_base_row(ocf_per_share=2.5, eps=1.8))
        s = CashflowQualityStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert mask.iloc[0]

    async def test_miss_low_cashflow(self) -> None:
        df = _make_df(_base_row(ocf_per_share=0.5, eps=1.8))
        s = CashflowQualityStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_negative_eps(self) -> None:
        df = _make_df(_base_row(ocf_per_share=2.0, eps=-0.5))
        s = CashflowQualityStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_nan_ocf(self) -> None:
        df = _make_df(_base_row(ocf_per_share=np.nan, eps=1.0))
        s = CashflowQualityStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]


# ============================================================
# 净利润连续增长策略
# ============================================================


class TestProfitContinuousGrowthStrategy:
    """净利润连续增长策略测试。"""

    async def test_hit_growth(self) -> None:
        df = _make_df(_base_row(profit_yoy=15.0))
        s = ProfitContinuousGrowthStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert mask.iloc[0]

    async def test_miss_low_growth(self) -> None:
        df = _make_df(_base_row(profit_yoy=3.0))
        s = ProfitContinuousGrowthStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_negative_growth(self) -> None:
        df = _make_df(_base_row(profit_yoy=-10.0))
        s = ProfitContinuousGrowthStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]


# ============================================================
# 经营现金流覆盖策略
# ============================================================


class TestCashflowCoverageStrategy:
    """经营现金流覆盖策略测试。"""

    async def test_hit_good_coverage(self) -> None:
        df = _make_df(_base_row(ocf_per_share=1.2, current_ratio=1.8))
        s = CashflowCoverageStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert mask.iloc[0]

    async def test_miss_low_ocf(self) -> None:
        df = _make_df(_base_row(ocf_per_share=0.2, current_ratio=1.5))
        s = CashflowCoverageStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_low_current_ratio(self) -> None:
        df = _make_df(_base_row(ocf_per_share=1.0, current_ratio=0.8))
        s = CashflowCoverageStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_nan(self) -> None:
        df = _make_df(_base_row(ocf_per_share=np.nan, current_ratio=1.5))
        s = CashflowCoverageStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]


# ============================================================
# 综合质量评分策略
# ============================================================


class TestQualityScoreStrategy:
    """综合质量评分策略测试。"""

    async def test_hit_high_quality(self) -> None:
        """高质量股票：ROE=22, profit_yoy=25, debt_ratio=35, pe_ttm=12 → 评分 86。"""
        df = _make_df(_base_row(roe=22.0, profit_yoy=25.0, debt_ratio=35.0, pe_ttm=12.0))
        s = QualityScoreStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert mask.iloc[0]

    async def test_miss_low_quality(self) -> None:
        """低质量股票：ROE=3, profit_yoy=-5, debt_ratio=70, pe_ttm=50 → 评分 20。"""
        df = _make_df(_base_row(roe=3.0, profit_yoy=-5.0, debt_ratio=70.0, pe_ttm=50.0))
        s = QualityScoreStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_nan_roe(self) -> None:
        """关键数据缺失时不评分。"""
        df = _make_df(_base_row(roe=np.nan, profit_yoy=25.0, debt_ratio=35.0, pe_ttm=12.0))
        s = QualityScoreStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_miss_negative_pe(self) -> None:
        """PE 为负（亏损）时不评分。"""
        df = _make_df(_base_row(roe=20.0, profit_yoy=25.0, debt_ratio=35.0, pe_ttm=-5.0))
        s = QualityScoreStrategy()
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]

    async def test_custom_threshold(self) -> None:
        """自定义阈值 score_min=80，中等质量股票不命中。"""
        df = _make_df(_base_row(roe=12.0, profit_yoy=12.0, debt_ratio=45.0, pe_ttm=18.0))
        s = QualityScoreStrategy(params={"score_min": 80.0})
        mask = await s.filter_batch(df, TARGET_DATE)
        assert not mask.iloc[0]


# ============================================================
# 策略工厂注册验证
# ============================================================


class TestStrategyFactoryFundamentalExpanded:
    """策略工厂基本面扩展验证。"""

    def test_registry_has_28_strategies(self) -> None:
        assert len(STRATEGY_REGISTRY) == 28

    def test_12_fundamental_strategies(self) -> None:
        fundamental = [m for m in STRATEGY_REGISTRY.values() if m.category == "fundamental"]
        assert len(fundamental) == 12

    def test_16_technical_strategies(self) -> None:
        technical = [m for m in STRATEGY_REGISTRY.values() if m.category == "technical"]
        assert len(technical) == 16

    def test_new_strategies_registered(self) -> None:
        new_names = [
            "pb-value", "peg-value", "ps-value",
            "gross-margin-up", "cashflow-quality", "profit-continuous-growth",
            "cashflow-coverage", "quality-score",
        ]
        for name in new_names:
            assert name in STRATEGY_REGISTRY, f"策略 {name} 未注册"

    def test_get_strategy_instances(self) -> None:
        new_names = [
            "pb-value", "peg-value", "ps-value",
            "gross-margin-up", "cashflow-quality", "profit-continuous-growth",
            "cashflow-coverage", "quality-score",
        ]
        for name in new_names:
            s = StrategyFactory.get_strategy(name)
            assert s.name == name
