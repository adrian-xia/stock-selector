"""测试各策略的 filter_batch 逻辑。

构造 DataFrame 验证布尔输出。
"""

from datetime import date

import pandas as pd
import pytest

from app.strategy.technical.ma_cross import MACrossStrategy
from app.strategy.technical.macd_golden import MACDGoldenStrategy
from app.strategy.technical.rsi_oversold import RSIOversoldStrategy
from app.strategy.technical.kdj_golden import KDJGoldenStrategy
from app.strategy.technical.boll_breakthrough import BollBreakthroughStrategy
from app.strategy.technical.volume_breakout import VolumeBreakoutStrategy
from app.strategy.technical.ma_long_arrange import MALongArrangeStrategy
from app.strategy.technical.macd_divergence import MACDDivergenceStrategy
from app.strategy.fundamental.low_pe_high_roe import LowPEHighROEStrategy
from app.strategy.fundamental.high_dividend import HighDividendStrategy
from app.strategy.fundamental.growth_stock import GrowthStockStrategy
from app.strategy.fundamental.financial_safety import FinancialSafetyStrategy

TARGET_DATE = date(2026, 2, 7)


# ---------------------------------------------------------------------------
# 技术面策略测试
# ---------------------------------------------------------------------------

class TestMACrossStrategy:
    """均线金叉策略测试。"""

    @pytest.mark.asyncio
    async def test_golden_cross_detected(self) -> None:
        """昨日 MA5 <= MA10，今日 MA5 > MA10，放量 → True。"""
        df = pd.DataFrame({
            "ma5": [11.0], "ma10": [10.0],
            "ma5_prev": [9.0], "ma10_prev": [10.0],
            "vol_ratio": [2.0], "vol": [1000.0],
        })
        s = MACrossStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] is True or result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_cross(self) -> None:
        """MA5 一直在 MA10 上方（无交叉）→ False。"""
        df = pd.DataFrame({
            "ma5": [12.0], "ma10": [10.0],
            "ma5_prev": [11.0], "ma10_prev": [10.0],
            "vol_ratio": [2.0], "vol": [1000.0],
        })
        s = MACrossStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_low_volume_rejected(self) -> None:
        """金叉但量比不足 → False。"""
        df = pd.DataFrame({
            "ma5": [11.0], "ma10": [10.0],
            "ma5_prev": [9.0], "ma10_prev": [10.0],
            "vol_ratio": [1.0], "vol": [1000.0],
        })
        s = MACrossStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestMACDGoldenStrategy:
    """MACD 金叉策略测试。"""

    @pytest.mark.asyncio
    async def test_golden_cross(self) -> None:
        df = pd.DataFrame({
            "macd_dif": [0.5], "macd_dea": [0.3],
            "macd_dif_prev": [0.2], "macd_dea_prev": [0.3],
            "vol": [1000.0],
        })
        s = MACDGoldenStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_cross(self) -> None:
        df = pd.DataFrame({
            "macd_dif": [0.5], "macd_dea": [0.3],
            "macd_dif_prev": [0.4], "macd_dea_prev": [0.3],
            "vol": [1000.0],
        })
        s = MACDGoldenStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestRSIOversoldStrategy:
    """RSI 超卖反弹策略测试。"""

    @pytest.mark.asyncio
    async def test_bounce_from_oversold(self) -> None:
        df = pd.DataFrame({
            "rsi6": [32.0], "rsi6_prev": [18.0], "vol": [1000.0],
        })
        s = RSIOversoldStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_not_oversold(self) -> None:
        df = pd.DataFrame({
            "rsi6": [55.0], "rsi6_prev": [50.0], "vol": [1000.0],
        })
        s = RSIOversoldStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestKDJGoldenStrategy:
    """KDJ 金叉策略测试。"""

    @pytest.mark.asyncio
    async def test_golden_cross_oversold(self) -> None:
        df = pd.DataFrame({
            "kdj_k": [25.0], "kdj_d": [20.0], "kdj_j": [15.0],
            "kdj_k_prev": [18.0], "kdj_d_prev": [20.0],
            "vol": [1000.0],
        })
        s = KDJGoldenStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_cross_but_not_oversold(self) -> None:
        df = pd.DataFrame({
            "kdj_k": [60.0], "kdj_d": [55.0], "kdj_j": [70.0],
            "kdj_k_prev": [50.0], "kdj_d_prev": [55.0],
            "vol": [1000.0],
        })
        s = KDJGoldenStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestBollBreakthroughStrategy:
    """布林带突破策略测试。"""

    @pytest.mark.asyncio
    async def test_bounce_from_lower(self) -> None:
        df = pd.DataFrame({
            "close": [10.5], "boll_lower": [10.0],
            "close_prev": [9.5], "boll_lower_prev": [10.0],
            "vol": [1000.0],
        })
        s = BollBreakthroughStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712


class TestVolumeBreakoutStrategy:
    """放量突破策略测试。"""

    @pytest.mark.asyncio
    async def test_breakout_with_volume(self) -> None:
        df = pd.DataFrame({
            "close": [15.0], "ma20": [13.0],
            "vol_ratio": [2.5], "vol": [1000.0],
        })
        s = VolumeBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_low_volume_ratio(self) -> None:
        df = pd.DataFrame({
            "close": [15.0], "ma20": [13.0],
            "vol_ratio": [1.0], "vol": [1000.0],
        })
        s = VolumeBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestMALongArrangeStrategy:
    """均线多头排列策略测试。"""

    @pytest.mark.asyncio
    async def test_bullish_alignment(self) -> None:
        df = pd.DataFrame({
            "ma5": [15.0], "ma10": [14.0], "ma20": [13.0], "ma60": [12.0],
            "vol": [1000.0],
        })
        s = MALongArrangeStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_partial_alignment(self) -> None:
        df = pd.DataFrame({
            "ma5": [15.0], "ma10": [14.0], "ma20": [13.0], "ma60": [14.5],
            "vol": [1000.0],
        })
        s = MALongArrangeStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestMACDDivergenceStrategy:
    """MACD 底背离策略测试。"""

    @pytest.mark.asyncio
    async def test_divergence_detected(self) -> None:
        df = pd.DataFrame({
            "close": [9.0], "macd_dif": [-0.3],
            "close_prev": [10.0], "macd_dif_prev": [-0.5],
            "vol": [1000.0],
        })
        s = MACDDivergenceStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712


# ---------------------------------------------------------------------------
# 基本面策略测试
# ---------------------------------------------------------------------------

class TestLowPEHighROEStrategy:
    """低估值高成长策略测试。"""

    @pytest.mark.asyncio
    async def test_meets_criteria(self) -> None:
        df = pd.DataFrame({
            "pe_ttm": [15.0], "roe": [20.0], "profit_yoy": [25.0],
        })
        s = LowPEHighROEStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_negative_pe_excluded(self) -> None:
        df = pd.DataFrame({
            "pe_ttm": [-5.0], "roe": [20.0], "profit_yoy": [25.0],
        })
        s = LowPEHighROEStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_high_pe_excluded(self) -> None:
        df = pd.DataFrame({
            "pe_ttm": [50.0], "roe": [20.0], "profit_yoy": [25.0],
        })
        s = LowPEHighROEStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestHighDividendStrategy:
    """高股息策略测试。"""

    @pytest.mark.asyncio
    async def test_high_dividend(self) -> None:
        df = pd.DataFrame({
            "dividend_yield": [4.5], "pe_ttm": [12.0],
        })
        s = HighDividendStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_low_dividend(self) -> None:
        df = pd.DataFrame({
            "dividend_yield": [1.0], "pe_ttm": [12.0],
        })
        s = HighDividendStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestGrowthStockStrategy:
    """成长股策略测试。"""

    @pytest.mark.asyncio
    async def test_high_growth(self) -> None:
        df = pd.DataFrame({
            "revenue_yoy": [30.0], "profit_yoy": [25.0],
        })
        s = GrowthStockStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_low_growth(self) -> None:
        df = pd.DataFrame({
            "revenue_yoy": [10.0], "profit_yoy": [25.0],
        })
        s = GrowthStockStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestFinancialSafetyStrategy:
    """财务安全策略测试。"""

    @pytest.mark.asyncio
    async def test_safe(self) -> None:
        df = pd.DataFrame({
            "debt_ratio": [45.0], "current_ratio": [2.0],
        })
        s = FinancialSafetyStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_high_debt(self) -> None:
        df = pd.DataFrame({
            "debt_ratio": [75.0], "current_ratio": [2.0],
        })
        s = FinancialSafetyStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_low_liquidity(self) -> None:
        df = pd.DataFrame({
            "debt_ratio": [45.0], "current_ratio": [1.0],
        })
        s = FinancialSafetyStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


# ---------------------------------------------------------------------------
# 通用测试：NaN 处理和不可变性
# ---------------------------------------------------------------------------

class TestStrategyNaNHandling:
    """测试策略对 NaN 值的处理。"""

    @pytest.mark.asyncio
    async def test_nan_returns_false(self) -> None:
        """包含 NaN 的行应返回 False。"""
        df = pd.DataFrame({
            "ma5": [float("nan")], "ma10": [10.0],
            "ma5_prev": [9.0], "ma10_prev": [10.0],
            "vol_ratio": [2.0], "vol": [1000.0],
        })
        s = MACrossStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestStrategyImmutability:
    """测试策略不修改输入 DataFrame。"""

    @pytest.mark.asyncio
    async def test_df_not_mutated(self) -> None:
        df = pd.DataFrame({
            "ma5": [11.0], "ma10": [10.0],
            "ma5_prev": [9.0], "ma10_prev": [10.0],
            "vol_ratio": [2.0], "vol": [1000.0],
        })
        original = df.copy()
        s = MACrossStrategy()
        await s.filter_batch(df, TARGET_DATE)
        pd.testing.assert_frame_equal(df, original)
