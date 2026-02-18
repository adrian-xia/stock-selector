"""新增 8 种技术面策略的单元测试。

覆盖：
- 趋势跟踪：DonchianBreakoutStrategy、ATRBreakoutStrategy
- 震荡指标：CCIOverboughtOversoldStrategy、WilliamsRStrategy、BIASStrategy
- 量价分析：VolumeContractionPullbackStrategy、VolumePriceDivergenceStrategy、OBVBreakthroughStrategy
- 策略工厂：注册表验证
"""

from datetime import date

import pandas as pd
import pytest

from app.strategy.technical.donchian_breakout import DonchianBreakoutStrategy
from app.strategy.technical.atr_breakout import ATRBreakoutStrategy
from app.strategy.technical.cci_oversold import CCIOverboughtOversoldStrategy
from app.strategy.technical.williams_r import WilliamsRStrategy
from app.strategy.technical.bias_oversold import BIASStrategy
from app.strategy.technical.volume_contraction import VolumeContractionPullbackStrategy
from app.strategy.technical.volume_price_divergence import VolumePriceDivergenceStrategy
from app.strategy.technical.obv_breakthrough import OBVBreakthroughStrategy
from app.strategy.factory import StrategyFactory

TARGET_DATE = date(2026, 2, 18)


def _base_row(**overrides) -> dict:
    """构造单行策略测试数据，默认值为"不触发"状态。"""
    row = {
        "ts_code": "000001.SZ",
        "close": 10.0,
        "close_prev": 10.0,
        "vol": 1000.0,
        # 均线
        "ma5": 10.0,
        "ma20": 10.0,
        "ma20_prev": 10.0,
        # ATR
        "atr14": 0.5,
        "atr14_prev": 0.5,
        # 唐奇安通道
        "donchian_upper": 11.0,
        "donchian_upper_prev": 11.0,
        "donchian_lower": 9.0,
        # 震荡指标
        "cci": 0.0,
        "cci_prev": 0.0,
        "wr": -50.0,
        "wr_prev": -50.0,
        "bias": 0.0,
        # 量价
        "vol_ratio": 1.0,
        "obv": 1000.0,
        "obv_prev": 900.0,
    }
    row.update(overrides)
    return row


# ============================================================
# 7.2 趋势跟踪策略测试
# ============================================================


class TestDonchianBreakoutStrategy:
    """测试唐奇安通道突破策略。"""

    @pytest.mark.asyncio
    async def test_breakout_signal(self):
        """昨日收盘 <= 上轨，今日收盘 > 上轨 → 触发。"""
        df = pd.DataFrame([_base_row(
            close=11.5, close_prev=10.5,
            donchian_upper=11.0, donchian_upper_prev=11.0,
        )])
        s = DonchianBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] is True or result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_already_above(self):
        """昨日已在上轨之上 → 不触发。"""
        df = pd.DataFrame([_base_row(
            close=12.0, close_prev=11.5,
            donchian_upper=11.0, donchian_upper_prev=11.0,
        )])
        s = DonchianBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_below(self):
        """今日收盘仍低于上轨 → 不触发。"""
        df = pd.DataFrame([_base_row(
            close=10.5, close_prev=10.0,
            donchian_upper=11.0, donchian_upper_prev=11.0,
        )])
        s = DonchianBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_suspended_excluded(self):
        """停牌（vol=0）排除。"""
        df = pd.DataFrame([_base_row(
            close=11.5, close_prev=10.5,
            donchian_upper=11.0, donchian_upper_prev=11.0,
            vol=0,
        )])
        s = DonchianBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestATRBreakoutStrategy:
    """测试 ATR 波动率突破策略。"""

    @pytest.mark.asyncio
    async def test_breakout_signal(self):
        """今日突破 MA20 + ATR*1.5，昨日未突破 → 触发。"""
        # upper_band = 10.0 + 0.5 * 1.5 = 10.75
        df = pd.DataFrame([_base_row(
            close=11.0, close_prev=10.5,
            ma20=10.0, ma20_prev=10.0,
            atr14=0.5, atr14_prev=0.5,
        )])
        s = ATRBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_below_band(self):
        """今日未突破上轨 → 不触发。"""
        # upper_band = 10.0 + 0.5 * 1.5 = 10.75
        df = pd.DataFrame([_base_row(
            close=10.5, close_prev=10.0,
            ma20=10.0, ma20_prev=10.0,
            atr14=0.5, atr14_prev=0.5,
        )])
        s = ATRBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_already_above(self):
        """昨日已在上轨之上 → 不触发。"""
        # prev_upper = 10.0 + 0.5 * 1.5 = 10.75, prev_close=11.0 > 10.75
        df = pd.DataFrame([_base_row(
            close=11.0, close_prev=11.0,
            ma20=10.0, ma20_prev=10.0,
            atr14=0.5, atr14_prev=0.5,
        )])
        s = ATRBreakoutStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_custom_multiplier(self):
        """自定义 atr_multiplier=2.0。"""
        # upper_band = 10.0 + 0.5 * 2.0 = 11.0
        df = pd.DataFrame([_base_row(
            close=11.5, close_prev=10.5,
            ma20=10.0, ma20_prev=10.0,
            atr14=0.5, atr14_prev=0.5,
        )])
        s = ATRBreakoutStrategy(params={"atr_multiplier": 2.0})
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712


# ============================================================
# 7.3 震荡指标策略测试
# ============================================================


class TestCCIOverboughtOversoldStrategy:
    """测试 CCI 超买超卖策略。"""

    @pytest.mark.asyncio
    async def test_bounce_signal(self):
        """昨日 CCI <= -100，今日 CCI > -80 → 触发。"""
        df = pd.DataFrame([_base_row(cci=-70.0, cci_prev=-110.0)])
        s = CCIOverboughtOversoldStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_still_oversold(self):
        """昨日 CCI <= -100，今日 CCI 仍 <= -80 → 不触发。"""
        df = pd.DataFrame([_base_row(cci=-90.0, cci_prev=-110.0)])
        s = CCIOverboughtOversoldStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_prev_not_oversold(self):
        """昨日 CCI > -100 → 不触发。"""
        df = pd.DataFrame([_base_row(cci=-70.0, cci_prev=-90.0)])
        s = CCIOverboughtOversoldStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_suspended_excluded(self):
        """停牌排除。"""
        df = pd.DataFrame([_base_row(cci=-70.0, cci_prev=-110.0, vol=0)])
        s = CCIOverboughtOversoldStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestWilliamsRStrategy:
    """测试 Williams %R 超卖反弹策略。"""

    @pytest.mark.asyncio
    async def test_bounce_signal(self):
        """昨日 WR <= -80，今日 WR > -50 → 触发。"""
        df = pd.DataFrame([_base_row(wr=-40.0, wr_prev=-85.0)])
        s = WilliamsRStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_still_oversold(self):
        """昨日 WR <= -80，今日 WR 仍 <= -50 → 不触发。"""
        df = pd.DataFrame([_base_row(wr=-60.0, wr_prev=-85.0)])
        s = WilliamsRStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_prev_not_oversold(self):
        """昨日 WR > -80 → 不触发。"""
        df = pd.DataFrame([_base_row(wr=-40.0, wr_prev=-70.0)])
        s = WilliamsRStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestBIASStrategy:
    """测试 BIAS 乖离率策略。"""

    @pytest.mark.asyncio
    async def test_oversold_signal(self):
        """BIAS <= -6.0 → 触发。"""
        df = pd.DataFrame([_base_row(bias=-7.0)])
        s = BIASStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_above_threshold(self):
        """BIAS > -6.0 → 不触发。"""
        df = pd.DataFrame([_base_row(bias=-5.0)])
        s = BIASStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_exact_threshold(self):
        """BIAS == -6.0 → 触发（<=）。"""
        df = pd.DataFrame([_base_row(bias=-6.0)])
        s = BIASStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        """自定义 oversold_bias=-8.0。"""
        df = pd.DataFrame([_base_row(bias=-7.0)])
        s = BIASStrategy(params={"oversold_bias": -8.0})
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


# ============================================================
# 7.4 量价分析策略测试
# ============================================================


class TestVolumeContractionPullbackStrategy:
    """测试缩量回调策略。"""

    @pytest.mark.asyncio
    async def test_signal(self):
        """上升趋势 + 缩量 + 回调至 MA20 附近 → 触发。"""
        df = pd.DataFrame([_base_row(
            close=10.1, ma5=10.5, ma20=10.0, vol_ratio=0.5,
        )])
        s = VolumeContractionPullbackStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_downtrend(self):
        """下降趋势（MA5 < MA20）→ 不触发。"""
        df = pd.DataFrame([_base_row(
            close=10.0, ma5=9.5, ma20=10.0, vol_ratio=0.5,
        )])
        s = VolumeContractionPullbackStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_high_volume(self):
        """量比过高 → 不触发。"""
        df = pd.DataFrame([_base_row(
            close=10.0, ma5=10.5, ma20=10.0, vol_ratio=1.5,
        )])
        s = VolumeContractionPullbackStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_far_from_ma20(self):
        """价格远离 MA20 → 不触发。"""
        df = pd.DataFrame([_base_row(
            close=12.0, ma5=12.5, ma20=10.0, vol_ratio=0.5,
        )])
        s = VolumeContractionPullbackStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestVolumePriceDivergenceStrategy:
    """测试量价背离策略。"""

    @pytest.mark.asyncio
    async def test_signal(self):
        """价格接近唐奇安下轨 + 量比萎缩 → 触发。"""
        df = pd.DataFrame([_base_row(
            close=9.1, donchian_lower=9.0, vol_ratio=0.5,
        )])
        s = VolumePriceDivergenceStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_price_far_from_low(self):
        """价格远离下轨 → 不触发。"""
        df = pd.DataFrame([_base_row(
            close=10.0, donchian_lower=9.0, vol_ratio=0.5,
        )])
        s = VolumePriceDivergenceStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_high_volume(self):
        """量比不萎缩 → 不触发。"""
        df = pd.DataFrame([_base_row(
            close=9.1, donchian_lower=9.0, vol_ratio=1.0,
        )])
        s = VolumePriceDivergenceStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


class TestOBVBreakthroughStrategy:
    """测试 OBV 能量潮突破策略。"""

    @pytest.mark.asyncio
    async def test_signal(self):
        """OBV 上升 + 价格上涨 → 触发。"""
        df = pd.DataFrame([_base_row(
            obv=1100.0, obv_prev=1000.0,
            close=10.5, close_prev=10.0,
        )])
        s = OBVBreakthroughStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == True  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_obv_down(self):
        """OBV 下降 → 不触发。"""
        df = pd.DataFrame([_base_row(
            obv=900.0, obv_prev=1000.0,
            close=10.5, close_prev=10.0,
        )])
        s = OBVBreakthroughStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_no_signal_price_down(self):
        """价格下跌（无确认）→ 不触发。"""
        df = pd.DataFrame([_base_row(
            obv=1100.0, obv_prev=1000.0,
            close=9.5, close_prev=10.0,
        )])
        s = OBVBreakthroughStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712

    @pytest.mark.asyncio
    async def test_suspended_excluded(self):
        """停牌排除。"""
        df = pd.DataFrame([_base_row(
            obv=1100.0, obv_prev=1000.0,
            close=10.5, close_prev=10.0, vol=0,
        )])
        s = OBVBreakthroughStrategy()
        result = await s.filter_batch(df, TARGET_DATE)
        assert result.iloc[0] == False  # noqa: E712


# ============================================================
# 7.5 策略工厂注册表测试
# ============================================================


class TestStrategyFactoryExpanded:
    """测试策略工厂注册表包含 20 个策略。"""

    def test_total_count(self):
        """验证注册表共 20 个策略。"""
        all_strategies = StrategyFactory.get_all()
        assert len(all_strategies) == 20

    def test_technical_count(self):
        """验证技术面策略 16 个。"""
        tech = StrategyFactory.get_by_category("technical")
        assert len(tech) == 16

    def test_fundamental_count(self):
        """验证基本面策略 4 个。"""
        fund = StrategyFactory.get_by_category("fundamental")
        assert len(fund) == 4

    def test_new_strategies_registered(self):
        """验证 8 个新策略都已注册。"""
        new_names = [
            "donchian-breakout", "atr-breakout",
            "cci-oversold", "williams-r", "bias-oversold",
            "volume-contraction-pullback", "volume-price-divergence",
            "obv-breakthrough",
        ]
        all_names = [m.name for m in StrategyFactory.get_all()]
        for name in new_names:
            assert name in all_names, f"策略 {name} 未注册"

    def test_instantiate_new_strategies(self):
        """验证 8 个新策略都能正常实例化。"""
        new_names = [
            "donchian-breakout", "atr-breakout",
            "cci-oversold", "williams-r", "bias-oversold",
            "volume-contraction-pullback", "volume-price-divergence",
            "obv-breakthrough",
        ]
        for name in new_names:
            strategy = StrategyFactory.get_strategy(name)
            assert strategy is not None
            assert strategy.category == "technical"
