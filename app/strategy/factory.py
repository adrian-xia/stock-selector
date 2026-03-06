"""策略工厂：注册、查询和实例化策略。

V1 使用手动字典注册，所有策略在模块底部显式注册。
V2 新增双注册表：STRATEGY_REGISTRY（V1）+ STRATEGY_REGISTRY_V2（V2）。
"""

from dataclasses import dataclass, field

from app.strategy.base import BaseStrategy, BaseStrategyV2, SignalGroup, StrategyRole


@dataclass(frozen=True)
class StrategyMeta:
    """策略元数据（V1），描述一个策略的静态信息。"""

    name: str                          # 唯一标识，如 "ma-cross"
    display_name: str                  # 显示名称，如 "均线金叉"
    category: str                      # "technical" 或 "fundamental"
    description: str                   # 一句话描述
    strategy_cls: type[BaseStrategy]   # 策略类引用
    default_params: dict = field(default_factory=dict)
    param_space: dict = field(default_factory=dict)  # 可优化参数空间


@dataclass(frozen=True)
class StrategyMetaV2:
    """策略元数据（V2）。"""

    name: str
    display_name: str
    role: StrategyRole
    signal_group: SignalGroup | None
    description: str
    strategy_cls: type[BaseStrategyV2]
    ai_rating: float  # 三模型综合均分
    default_params: dict = field(default_factory=dict)
    param_space: dict = field(default_factory=dict)
    style_keys: list[str] = field(default_factory=list)  # tagger 可产出的风格标签键（元数据）


# V1 策略注册表：name -> StrategyMeta
STRATEGY_REGISTRY: dict[str, StrategyMeta] = {}

# V2 策略注册表：name -> StrategyMetaV2
STRATEGY_REGISTRY_V2: dict[str, StrategyMetaV2] = {}


class StrategyFactory:
    """策略工厂，提供策略的查询和实例化能力（V1）。"""

    @classmethod
    def get_strategy(
        cls,
        name: str,
        params: dict | None = None,
    ) -> BaseStrategy:
        """根据策略名称实例化策略对象。

        Args:
            name: 策略唯一标识
            params: 运行时参数（覆盖默认值）

        Returns:
            策略实例

        Raises:
            KeyError: 策略未注册
        """
        if name not in STRATEGY_REGISTRY:
            available = list(STRATEGY_REGISTRY.keys())
            raise KeyError(
                f"策略 '{name}' 未注册，可用策略：{available}"
            )
        meta = STRATEGY_REGISTRY[name]
        return meta.strategy_cls(params=params)

    @classmethod
    def get_all(cls) -> list[StrategyMeta]:
        """获取所有已注册策略的元数据列表。"""
        return list(STRATEGY_REGISTRY.values())

    @classmethod
    def get_by_category(cls, category: str) -> list[StrategyMeta]:
        """按分类查询策略。

        Args:
            category: "technical" 或 "fundamental"

        Returns:
            匹配分类的策略元数据列表
        """
        return [
            m for m in STRATEGY_REGISTRY.values()
            if m.category == category
        ]

    @classmethod
    def get_meta(cls, name: str) -> StrategyMeta:
        """获取指定策略的元数据。

        Args:
            name: 策略唯一标识

        Returns:
            策略元数据

        Raises:
            KeyError: 策略未注册
        """
        if name not in STRATEGY_REGISTRY:
            available = list(STRATEGY_REGISTRY.keys())
            raise KeyError(
                f"策略 '{name}' 未注册，可用策略：{available}"
            )
        return STRATEGY_REGISTRY[name]


class StrategyFactoryV2:
    """策略工厂（V2），提供 V2 策略的查询和实例化能力。"""

    @classmethod
    def get_strategy(
        cls,
        name: str,
        params: dict | None = None,
    ) -> BaseStrategyV2:
        """根据策略名称实例化 V2 策略对象。

        Args:
            name: 策略唯一标识
            params: 运行时参数（覆盖默认值）

        Returns:
            V2 策略实例

        Raises:
            KeyError: 策略未注册
        """
        if name not in STRATEGY_REGISTRY_V2:
            available = list(STRATEGY_REGISTRY_V2.keys())
            raise KeyError(
                f"V2 策略 '{name}' 未注册，可用策略：{available}"
            )
        meta = STRATEGY_REGISTRY_V2[name]
        return meta.strategy_cls(params=params)

    @classmethod
    def get_all(cls) -> list[StrategyMetaV2]:
        """获取所有已注册 V2 策略的元数据列表。"""
        return list(STRATEGY_REGISTRY_V2.values())

    @classmethod
    def get_by_role(cls, role: StrategyRole) -> list[StrategyMetaV2]:
        """按角色查询 V2 策略。

        Args:
            role: StrategyRole 枚举值

        Returns:
            匹配角色的策略元数据列表
        """
        return [
            m for m in STRATEGY_REGISTRY_V2.values()
            if m.role == role
        ]

    @classmethod
    def get_by_signal_group(cls, signal_group: SignalGroup) -> list[StrategyMetaV2]:
        """按信号组查询 V2 trigger 策略。

        Args:
            signal_group: SignalGroup 枚举值

        Returns:
            匹配信号组的 trigger 策略元数据列表
        """
        return [
            m for m in STRATEGY_REGISTRY_V2.values()
            if m.role == StrategyRole.TRIGGER and m.signal_group == signal_group
        ]

    @classmethod
    def get_meta(cls, name: str) -> StrategyMetaV2:
        """获取指定 V2 策略的元数据。

        Args:
            name: 策略唯一标识

        Returns:
            V2 策略元数据

        Raises:
            KeyError: 策略未注册
        """
        if name not in STRATEGY_REGISTRY_V2:
            available = list(STRATEGY_REGISTRY_V2.keys())
            raise KeyError(
                f"V2 策略 '{name}' 未注册，可用策略：{available}"
            )
        return STRATEGY_REGISTRY_V2[name]


def _register(meta: StrategyMeta) -> None:
    """内部注册函数，将 V1 策略元数据写入注册表。"""
    STRATEGY_REGISTRY[meta.name] = meta


def _register_v2(meta: StrategyMetaV2) -> None:
    """内部注册函数，将 V2 策略元数据写入注册表。"""
    STRATEGY_REGISTRY_V2[meta.name] = meta


# ---------------------------------------------------------------------------
# V2 策略注册：20 个策略
# ---------------------------------------------------------------------------

# Scorer（1 个）
from app.strategy.scorers.quality_score_v2 import QualityScoreStrategyV2  # noqa: E402

_register_v2(StrategyMetaV2(
    name="quality-score-v2",
    display_name="综合质量评分",
    role=StrategyRole.SCORER,
    signal_group=None,
    description="ROE+成长+安全+估值+毛利率变化，行业中性化Z-Score",
    strategy_cls=QualityScoreStrategyV2,
    ai_rating=7.80,
    default_params={},
))

# Confirmer（5 个）
from app.strategy.confirmers.ma_long_arrange_v2 import MALongArrangeConfirmerV2  # noqa: E402
from app.strategy.confirmers.rsi_oversold_v2 import RSIOversoldConfirmerV2  # noqa: E402
from app.strategy.confirmers.bias_extreme_v2 import BIASExtremeConfirmerV2  # noqa: E402
from app.strategy.confirmers.macd_divergence_v2 import MACDDivergenceConfirmerV2  # noqa: E402
from app.strategy.confirmers.shrink_volume_rise_v2 import ShrinkVolumeRiseConfirmerV2  # noqa: E402

_register_v2(StrategyMetaV2(
    name="ma-long-arrange-confirmer-v2",
    display_name="均线多头排列（确认）",
    role=StrategyRole.CONFIRMER,
    signal_group=None,
    description="趋势方向确认，为趋势组信号加分",
    strategy_cls=MALongArrangeConfirmerV2,
    ai_rating=6.53,
))

_register_v2(StrategyMetaV2(
    name="rsi-oversold-confirmer-v2",
    display_name="RSI超卖（确认）",
    role=StrategyRole.CONFIRMER,
    signal_group=None,
    description="仅MA20向上时启用，为底部信号加分",
    strategy_cls=RSIOversoldConfirmerV2,
    ai_rating=6.00,
))

_register_v2(StrategyMetaV2(
    name="bias-extreme-confirmer-v2",
    display_name="BIAS极端乖离（确认）",
    role=StrategyRole.CONFIRMER,
    signal_group=None,
    description="乖离率历史分位数<5%，为反弹信号加分",
    strategy_cls=BIASExtremeConfirmerV2,
    ai_rating=5.80,
))

_register_v2(StrategyMetaV2(
    name="macd-divergence-confirmer-v2",
    display_name="MACD底背离（确认）",
    role=StrategyRole.CONFIRMER,
    signal_group=None,
    description="二次底背离确认，为底部信号加分",
    strategy_cls=MACDDivergenceConfirmerV2,
    ai_rating=6.18,
))

_register_v2(StrategyMetaV2(
    name="shrink-volume-rise-confirmer-v2",
    display_name="缩量上涨（确认）",
    role=StrategyRole.CONFIRMER,
    signal_group=None,
    description="筹码锁定确认，为趋势延续信号加分",
    strategy_cls=ShrinkVolumeRiseConfirmerV2,
    ai_rating=6.87,
))

# Guard（2 个）
from app.strategy.guards import FinancialSafetyGuardV2, CashflowQualityGuardV2  # noqa: E402

_register_v2(StrategyMetaV2(
    name="financial-safety-guard-v2",
    display_name="财务安全（排雷）",
    role=StrategyRole.GUARD,
    signal_group=None,
    description="资产负债率/流动比率/速动比率",
    strategy_cls=FinancialSafetyGuardV2,
    ai_rating=6.72,
))

_register_v2(StrategyMetaV2(
    name="cashflow-quality-guard-v2",
    display_name="现金流质量（排雷）",
    role=StrategyRole.GUARD,
    signal_group=None,
    description="OCF/EPS>=1，排除纸面利润",
    strategy_cls=CashflowQualityGuardV2,
    ai_rating=7.33,
))

# Tagger（2 个）
from app.strategy.taggers import LowPEHighROETaggerV2, HighDividendTaggerV2  # noqa: E402

_register_v2(StrategyMetaV2(
    name="low-pe-high-roe-tagger-v2",
    display_name="低估值高成长（标签）",
    role=StrategyRole.TAGGER,
    signal_group=None,
    description="PE<30 + ROE>=15% + 利润增速>=20%",
    strategy_cls=LowPEHighROETaggerV2,
    ai_rating=7.62,
    style_keys=["growth"],
))

_register_v2(StrategyMetaV2(
    name="high-dividend-tagger-v2",
    display_name="高股息（标签）",
    role=StrategyRole.TAGGER,
    signal_group=None,
    description="股息率>=3% + PE<20",
    strategy_cls=HighDividendTaggerV2,
    ai_rating=8.08,
    style_keys=["dividend"],
))

# Trigger（10 个）
from app.strategy.triggers import (  # noqa: E402
    DragonTurnaroundTriggerV2,
    FirstNegativeReversalTriggerV2,
    VolumeBreakoutTriggerV2,
    VolumeSurgeContinuationTriggerV2,
    VolumeContractionPullbackTriggerV2,
    PeakPullbackStabilizationTriggerV2,
    PullbackHalfRuleTriggerV2,
    ATRBreakoutTriggerV2,
    ExtremeShrinkBottomTriggerV2,
    VolumePriceStableTriggerV2,
)

# 进攻组（4 个）
_register_v2(StrategyMetaV2(
    name="dragon-turnaround-trigger-v2",
    display_name="龙回头",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.AGGRESSIVE,
    description="放量突破后缩量回踩企稳，捕捉主升浪启动点",
    strategy_cls=DragonTurnaroundTriggerV2,
    ai_rating=8.32,
))

_register_v2(StrategyMetaV2(
    name="first-negative-reversal-trigger-v2",
    display_name="首阴反包",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.AGGRESSIVE,
    description="强势股首阴后阳线反包，多头重新占优",
    strategy_cls=FirstNegativeReversalTriggerV2,
    ai_rating=7.73,
))

_register_v2(StrategyMetaV2(
    name="volume-breakout-trigger-v2",
    display_name="放量突破",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.AGGRESSIVE,
    description="价格创近期新高且成交量显著放大",
    strategy_cls=VolumeBreakoutTriggerV2,
    ai_rating=7.42,
))

_register_v2(StrategyMetaV2(
    name="volume-surge-continuation-trigger-v2",
    display_name="后量超前量",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.AGGRESSIVE,
    description="资金加速流入，量能持续放大的趋势加速信号",
    strategy_cls=VolumeSurgeContinuationTriggerV2,
    ai_rating=6.93,
))

# 趋势组（4 个）
_register_v2(StrategyMetaV2(
    name="volume-contraction-pullback-trigger-v2",
    display_name="缩量回调",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.TREND,
    description="上升趋势中缩量回调至MA20支撑位",
    strategy_cls=VolumeContractionPullbackTriggerV2,
    ai_rating=7.42,
))

_register_v2(StrategyMetaV2(
    name="peak-pullback-stabilization-trigger-v2",
    display_name="高位回落企稳",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.TREND,
    description="前期主升浪后高位回落，缩量企稳后放量小阳二次启动",
    strategy_cls=PeakPullbackStabilizationTriggerV2,
    ai_rating=7.47,
))

_register_v2(StrategyMetaV2(
    name="pullback-half-rule-trigger-v2",
    display_name="回调半分位",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.TREND,
    description="多头排列中小幅回调不超半分位，多头力量仍强",
    strategy_cls=PullbackHalfRuleTriggerV2,
    ai_rating=7.00,
))

_register_v2(StrategyMetaV2(
    name="atr-breakout-trigger-v2",
    display_name="ATR波动率突破",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.TREND,
    description="价格突破MA20 + ATR14波动带上轨",
    strategy_cls=ATRBreakoutTriggerV2,
    ai_rating=6.97,
))

# 底部组（2 个）
_register_v2(StrategyMetaV2(
    name="extreme-shrink-bottom-trigger-v2",
    display_name="地量见底",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.BOTTOM,
    description="极端缩量+低换手率，阶段性底部信号",
    strategy_cls=ExtremeShrinkBottomTriggerV2,
    ai_rating=6.68,
))

_register_v2(StrategyMetaV2(
    name="volume-price-stable-trigger-v2",
    display_name="量缩价稳",
    role=StrategyRole.TRIGGER,
    signal_group=SignalGroup.BOTTOM,
    description="量缩价稳，抛压耗尽的底部企稳信号",
    strategy_cls=VolumePriceStableTriggerV2,
    ai_rating=6.68,
))


# ---------------------------------------------------------------------------
# 策略注册：技术面（16 种）V1
# ---------------------------------------------------------------------------
from app.strategy.technical.ma_cross import MACrossStrategy  # noqa: E402
from app.strategy.technical.macd_golden import MACDGoldenStrategy  # noqa: E402
from app.strategy.technical.rsi_oversold import RSIOversoldStrategy  # noqa: E402
from app.strategy.technical.kdj_golden import KDJGoldenStrategy  # noqa: E402
from app.strategy.technical.boll_breakthrough import BollBreakthroughStrategy  # noqa: E402
from app.strategy.technical.volume_breakout import VolumeBreakoutStrategy  # noqa: E402
from app.strategy.technical.ma_long_arrange import MALongArrangeStrategy  # noqa: E402
from app.strategy.technical.macd_divergence import MACDDivergenceStrategy  # noqa: E402
from app.strategy.technical.donchian_breakout import DonchianBreakoutStrategy  # noqa: E402
from app.strategy.technical.atr_breakout import ATRBreakoutStrategy  # noqa: E402
from app.strategy.technical.cci_oversold import CCIOverboughtOversoldStrategy  # noqa: E402
from app.strategy.technical.williams_r import WilliamsRStrategy  # noqa: E402
from app.strategy.technical.bias_oversold import BIASStrategy  # noqa: E402
from app.strategy.technical.volume_contraction import VolumeContractionPullbackStrategy  # noqa: E402
from app.strategy.technical.volume_price_divergence import VolumePriceDivergenceStrategy  # noqa: E402
from app.strategy.technical.obv_breakthrough import OBVBreakthroughStrategy  # noqa: E402
from app.strategy.technical.shrink_volume_rise import ShrinkVolumeRiseStrategy  # noqa: E402
from app.strategy.technical.volume_price_stable import VolumePriceStableStrategy  # noqa: E402
from app.strategy.technical.first_negative_reversal import FirstNegativeReversalStrategy  # noqa: E402
from app.strategy.technical.extreme_shrink_bottom import ExtremeShrinkBottomStrategy  # noqa: E402
from app.strategy.technical.volume_surge_continuation import VolumeSurgeContinuationStrategy  # noqa: E402
from app.strategy.technical.pullback_half_rule import PullbackHalfRuleStrategy  # noqa: E402
from app.strategy.technical.peak_pullback_stabilization import PeakPullbackStabilizationStrategy  # noqa: E402

# ---------------------------------------------------------------------------
# 策略注册：基本面（12 种）
# ---------------------------------------------------------------------------
from app.strategy.fundamental.low_pe_high_roe import LowPEHighROEStrategy  # noqa: E402
from app.strategy.fundamental.high_dividend import HighDividendStrategy  # noqa: E402
from app.strategy.fundamental.growth_stock import GrowthStockStrategy  # noqa: E402
from app.strategy.fundamental.financial_safety import FinancialSafetyStrategy  # noqa: E402
from app.strategy.fundamental.pb_value import PBValueStrategy  # noqa: E402
from app.strategy.fundamental.peg_value import PEGValueStrategy  # noqa: E402
from app.strategy.fundamental.ps_value import PSValueStrategy  # noqa: E402
from app.strategy.fundamental.gross_margin_up import GrossMarginUpStrategy  # noqa: E402
from app.strategy.fundamental.cashflow_quality import CashflowQualityStrategy  # noqa: E402
from app.strategy.fundamental.profit_continuous_growth import ProfitContinuousGrowthStrategy  # noqa: E402
from app.strategy.fundamental.cashflow_coverage import CashflowCoverageStrategy  # noqa: E402
from app.strategy.fundamental.quality_score import QualityScoreStrategy  # noqa: E402

# --- 技术面策略注册 ---
_register(StrategyMeta(
    name="ma-cross",
    display_name="均线金叉",
    category="technical",
    description="短期均线上穿长期均线，且成交量放大",
    strategy_cls=MACrossStrategy,
    default_params={"fast": 5, "slow": 10, "vol_ratio": 1.5},
    param_space={
        "fast": {"type": "int", "min": 3, "max": 20, "step": 1},
        "slow": {"type": "int", "min": 10, "max": 60, "step": 5},
        "vol_ratio": {"type": "float", "min": 1.0, "max": 3.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="macd-golden",
    display_name="MACD金叉",
    category="technical",
    description="MACD DIF线上穿DEA线，发出买入信号",
    strategy_cls=MACDGoldenStrategy,
))
_register(StrategyMeta(
    name="rsi-oversold",
    display_name="RSI超卖反弹",
    category="technical",
    description="RSI从超卖区域回升，发出反弹买入信号",
    strategy_cls=RSIOversoldStrategy,
    default_params={"period": 6, "oversold": 20, "bounce": 30},
    param_space={
        "period": {"type": "int", "min": 3, "max": 14, "step": 1},
        "oversold": {"type": "int", "min": 10, "max": 30, "step": 5},
        "bounce": {"type": "int", "min": 25, "max": 50, "step": 5},
    },
))
_register(StrategyMeta(
    name="kdj-golden",
    display_name="KDJ金叉",
    category="technical",
    description="KDJ K线上穿D线，且J值处于超卖区域",
    strategy_cls=KDJGoldenStrategy,
    default_params={"oversold_j": 20},
    param_space={
        "oversold_j": {"type": "int", "min": 0, "max": 30, "step": 5},
    },
))
_register(StrategyMeta(
    name="boll-breakthrough",
    display_name="布林带突破",
    category="technical",
    description="价格从布林带下轨下方回升，发出超跌反弹信号",
    strategy_cls=BollBreakthroughStrategy,
))
_register(StrategyMeta(
    name="volume-breakout",
    display_name="放量突破",
    category="technical",
    description="价格创近期新高且成交量显著放大",
    strategy_cls=VolumeBreakoutStrategy,
    default_params={"high_period": 20, "min_vol_ratio": 2.0},
    param_space={
        "high_period": {"type": "int", "min": 10, "max": 60, "step": 5},
        "min_vol_ratio": {"type": "float", "min": 1.5, "max": 4.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="ma-long-arrange",
    display_name="均线多头排列",
    category="technical",
    description="MA5 > MA10 > MA20 > MA60，强势上涨趋势",
    strategy_cls=MALongArrangeStrategy,
))
_register(StrategyMeta(
    name="macd-divergence",
    display_name="MACD底背离",
    category="technical",
    description="价格创近期新低但MACD DIF未创新低，下跌动能减弱",
    strategy_cls=MACDDivergenceStrategy,
    default_params={"lookback": 20},
    param_space={
        "lookback": {"type": "int", "min": 10, "max": 40, "step": 5},
    },
))
_register(StrategyMeta(
    name="donchian-breakout",
    display_name="唐奇安通道突破",
    category="technical",
    description="价格突破 20 日唐奇安通道上轨",
    strategy_cls=DonchianBreakoutStrategy,
    default_params={"period": 20},
    param_space={
        "period": {"type": "int", "min": 10, "max": 40, "step": 5},
    },
))
_register(StrategyMeta(
    name="atr-breakout",
    display_name="ATR波动率突破",
    category="technical",
    description="价格突破 MA20 + ATR14 波动带上轨",
    strategy_cls=ATRBreakoutStrategy,
    default_params={"atr_multiplier": 1.5},
    param_space={
        "atr_multiplier": {"type": "float", "min": 1.0, "max": 3.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="cci-oversold",
    display_name="CCI超买超卖",
    category="technical",
    description="CCI 从超卖区（<-100）反弹至 -80 以上",
    strategy_cls=CCIOverboughtOversoldStrategy,
    default_params={"oversold": -100, "bounce": -80},
    param_space={
        "oversold": {"type": "int", "min": -200, "max": -50, "step": 25},
        "bounce": {"type": "int", "min": -100, "max": -50, "step": 10},
    },
))
_register(StrategyMeta(
    name="williams-r",
    display_name="Williams %R超卖反弹",
    category="technical",
    description="Williams %R 从超卖区（<-80）反弹至 -50 以上",
    strategy_cls=WilliamsRStrategy,
    default_params={"oversold": -80, "bounce": -50},
    param_space={
        "oversold": {"type": "int", "min": -95, "max": -70, "step": 5},
        "bounce": {"type": "int", "min": -60, "max": -30, "step": 10},
    },
))
_register(StrategyMeta(
    name="bias-oversold",
    display_name="BIAS乖离率",
    category="technical",
    description="BIAS 乖离率达到超卖极值（<-6%），预期均值回归",
    strategy_cls=BIASStrategy,
    default_params={"oversold_bias": -6.0},
    param_space={
        "oversold_bias": {"type": "float", "min": -10.0, "max": -3.0, "step": 1.0},
    },
))
_register(StrategyMeta(
    name="volume-contraction-pullback",
    display_name="缩量回调",
    category="technical",
    description="上升趋势中缩量回调至 MA20 支撑位",
    strategy_cls=VolumeContractionPullbackStrategy,
    default_params={"max_vol_ratio": 0.6, "ma_tolerance": 0.02},
    param_space={
        "max_vol_ratio": {"type": "float", "min": 0.3, "max": 0.8, "step": 0.1},
        "ma_tolerance": {"type": "float", "min": 0.01, "max": 0.05, "step": 0.01},
    },
))
_register(StrategyMeta(
    name="volume-price-divergence",
    display_name="量价背离",
    category="technical",
    description="价格接近近期低点但成交量显著萎缩",
    strategy_cls=VolumePriceDivergenceStrategy,
    default_params={"lookback": 20},
    param_space={
        "lookback": {"type": "int", "min": 10, "max": 40, "step": 5},
    },
))
_register(StrategyMeta(
    name="obv-breakthrough",
    display_name="OBV能量潮突破",
    category="technical",
    description="OBV 突破近期高点且价格上涨确认",
    strategy_cls=OBVBreakthroughStrategy,
    default_params={"lookback": 20},
    param_space={
        "lookback": {"type": "int", "min": 10, "max": 40, "step": 5},
    },
))

# --- 基本面策略注册 ---
_register(StrategyMeta(
    name="low-pe-high-roe",
    display_name="低估值高成长",
    category="fundamental",
    description="市盈率低于30，ROE高于15%，利润同比增长超20%",
    strategy_cls=LowPEHighROEStrategy,
    default_params={"pe_max": 30, "roe_min": 15, "profit_growth_min": 20},
    param_space={
        "pe_max": {"type": "int", "min": 15, "max": 50, "step": 5},
        "roe_min": {"type": "int", "min": 8, "max": 25, "step": 1},
        "profit_growth_min": {"type": "int", "min": 10, "max": 40, "step": 5},
    },
))
_register(StrategyMeta(
    name="high-dividend",
    display_name="高股息",
    category="fundamental",
    description="股息率高于3%，市盈率低于20",
    strategy_cls=HighDividendStrategy,
    default_params={"min_dividend_yield": 3.0, "pe_max": 20},
    param_space={
        "min_dividend_yield": {"type": "float", "min": 1.0, "max": 6.0, "step": 0.5},
        "pe_max": {"type": "int", "min": 10, "max": 30, "step": 5},
    },
))
_register(StrategyMeta(
    name="growth-stock",
    display_name="成长股",
    category="fundamental",
    description="营收和利润同比增长均超过20%",
    strategy_cls=GrowthStockStrategy,
    default_params={"revenue_growth_min": 20, "profit_growth_min": 20},
    param_space={
        "revenue_growth_min": {"type": "int", "min": 10, "max": 50, "step": 5},
        "profit_growth_min": {"type": "int", "min": 10, "max": 50, "step": 5},
    },
))
_register(StrategyMeta(
    name="financial-safety",
    display_name="财务安全",
    category="fundamental",
    description="资产负债率低于60%，流动比率高于1.5",
    strategy_cls=FinancialSafetyStrategy,
    default_params={"debt_ratio_max": 60, "current_ratio_min": 1.5},
    param_space={
        "debt_ratio_max": {"type": "int", "min": 30, "max": 70, "step": 5},
        "current_ratio_min": {"type": "float", "min": 1.0, "max": 3.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="pb-value",
    display_name="PB低估值",
    category="fundamental",
    description="市净率低于2倍，适合重资产行业价值投资",
    strategy_cls=PBValueStrategy,
    default_params={"pb_max": 2.0},
    param_space={
        "pb_max": {"type": "float", "min": 0.5, "max": 5.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="peg-value",
    display_name="PEG估值",
    category="fundamental",
    description="PEG低于1，成长性被低估",
    strategy_cls=PEGValueStrategy,
    default_params={"peg_max": 1.0},
    param_space={
        "peg_max": {"type": "float", "min": 0.5, "max": 2.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="ps-value",
    display_name="市销率低估值",
    category="fundamental",
    description="市销率低于3倍，适合高成长公司",
    strategy_cls=PSValueStrategy,
    default_params={"ps_max": 3.0},
    param_space={
        "ps_max": {"type": "float", "min": 1.0, "max": 6.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="gross-margin-up",
    display_name="毛利率提升",
    category="fundamental",
    description="毛利率高于30%，盈利能力强",
    strategy_cls=GrossMarginUpStrategy,
    default_params={"gross_margin_min": 30.0},
    param_space={
        "gross_margin_min": {"type": "float", "min": 15.0, "max": 50.0, "step": 5.0},
    },
))
_register(StrategyMeta(
    name="cashflow-quality",
    display_name="现金流质量",
    category="fundamental",
    description="每股经营现金流大于每股收益，现金流质量高",
    strategy_cls=CashflowQualityStrategy,
    default_params={"ocf_eps_ratio_min": 1.0},
    param_space={
        "ocf_eps_ratio_min": {"type": "float", "min": 0.5, "max": 2.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="profit-continuous-growth",
    display_name="净利润连续增长",
    category="fundamental",
    description="利润同比增长率持续为正，成长性好",
    strategy_cls=ProfitContinuousGrowthStrategy,
    default_params={"profit_growth_min": 5.0},
    param_space={
        "profit_growth_min": {"type": "float", "min": 0.0, "max": 20.0, "step": 5.0},
    },
))
_register(StrategyMeta(
    name="cashflow-coverage",
    display_name="经营现金流覆盖",
    category="fundamental",
    description="经营现金流充裕且流动比率达标",
    strategy_cls=CashflowCoverageStrategy,
    default_params={"ocf_min": 0.5, "current_ratio_min": 1.0},
    param_space={
        "ocf_min": {"type": "float", "min": 0.0, "max": 2.0, "step": 0.5},
        "current_ratio_min": {"type": "float", "min": 0.5, "max": 2.5, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="quality-score",
    display_name="综合质量评分",
    category="fundamental",
    description="ROE+成长+安全+估值多因子加权评分",
    strategy_cls=QualityScoreStrategy,
    default_params={"score_min": 60.0},
    param_space={
        "score_min": {"type": "float", "min": 40.0, "max": 80.0, "step": 5.0},
    },
))

# ---------------------------------------------------------------------------
# 策略注册：量价策略（6 种）
# ---------------------------------------------------------------------------
_register(StrategyMeta(
    name="shrink-volume-rise",
    display_name="缩量上涨",
    category="technical",
    description="上升趋势中缩量上涨，筹码锁定良好",
    strategy_cls=ShrinkVolumeRiseStrategy,
    default_params={"max_vol_ratio": 0.8, "min_pct_chg": 0.5},
    param_space={
        "max_vol_ratio": {"type": "float", "min": 0.4, "max": 1.0, "step": 0.1},
        "min_pct_chg": {"type": "float", "min": 0.0, "max": 2.0, "step": 0.5},
    },
))
_register(StrategyMeta(
    name="volume-price-stable",
    display_name="量缩价稳",
    category="technical",
    description="量缩价稳，抛压耗尽的底部企稳信号",
    strategy_cls=VolumePriceStableStrategy,
    default_params={"max_vol_ratio": 0.5, "max_pct_chg": 2.0, "ma_position": 1.02},
    param_space={
        "max_vol_ratio": {"type": "float", "min": 0.3, "max": 0.8, "step": 0.1},
        "max_pct_chg": {"type": "float", "min": 1.0, "max": 3.0, "step": 0.5},
        "ma_position": {"type": "float", "min": 0.98, "max": 1.05, "step": 0.01},
    },
))
_register(StrategyMeta(
    name="first-negative-reversal",
    display_name="首阴反包",
    category="technical",
    description="强势股首阴后阳线反包，多头重新占优",
    strategy_cls=FirstNegativeReversalStrategy,
    default_params={"min_pct_chg": 2.0, "min_vol_ratio": 1.0},
    param_space={
        "min_pct_chg": {"type": "float", "min": 1.0, "max": 4.0, "step": 0.5},
        "min_vol_ratio": {"type": "float", "min": 0.8, "max": 2.0, "step": 0.2},
    },
))
_register(StrategyMeta(
    name="extreme-shrink-bottom",
    display_name="地量见底",
    category="technical",
    description="极端缩量+低换手率，阶段性底部信号",
    strategy_cls=ExtremeShrinkBottomStrategy,
    default_params={"extreme_ratio": 0.3, "max_turnover": 1.0},
    param_space={
        "extreme_ratio": {"type": "float", "min": 0.1, "max": 0.5, "step": 0.05},
        "max_turnover": {"type": "float", "min": 0.5, "max": 2.0, "step": 0.25},
    },
))
_register(StrategyMeta(
    name="volume-surge-continuation",
    display_name="后量超前量",
    category="technical",
    description="资金加速流入，量能持续放大的趋势加速信号",
    strategy_cls=VolumeSurgeContinuationStrategy,
    default_params={"surge_ratio": 2.0, "vol_ma_ratio": 1.2, "min_pct_chg": 1.0},
    param_space={
        "surge_ratio": {"type": "float", "min": 1.5, "max": 3.0, "step": 0.25},
        "vol_ma_ratio": {"type": "float", "min": 1.0, "max": 1.5, "step": 0.1},
        "min_pct_chg": {"type": "float", "min": 0.5, "max": 2.0, "step": 0.25},
    },
))
_register(StrategyMeta(
    name="pullback-half-rule",
    display_name="回调半分位",
    category="technical",
    description="多头排列中小幅回调不超半分位，多头力量仍强",
    strategy_cls=PullbackHalfRuleStrategy,
    default_params={"max_pullback_pct": 3.0, "max_vol_ratio": 0.8},
    param_space={
        "max_pullback_pct": {"type": "float", "min": 1.0, "max": 5.0, "step": 0.5},
        "max_vol_ratio": {"type": "float", "min": 0.5, "max": 1.0, "step": 0.1},
    },
))
_register(StrategyMeta(
    name="peak-pullback-stabilization",
    display_name="高位回落企稳",
    category="technical",
    description="前期主升浪后高位回落，缩量企稳后放量小阳二次启动",
    strategy_cls=PeakPullbackStabilizationStrategy,
    default_params={
        "min_peak_rise_pct": 20.0, "ma_tolerance": 0.03,
        "min_pullback_pct": 10.0, "max_pullback_pct": 35.0,
        "max_vol_ratio": 0.8, "ma5_band": 0.025,
        "min_pct_chg": 0.5, "max_pct_chg": 7.0, "min_signal_vol_ratio": 1.2,
    },
    param_space={
        "min_pullback_pct": {"type": "float", "min": 8.0, "max": 15.0, "step": 2.0},
        "max_pullback_pct": {"type": "float", "min": 25.0, "max": 40.0, "step": 5.0},
        "max_vol_ratio": {"type": "float", "min": 0.6, "max": 0.9, "step": 0.1},
        "ma5_band": {"type": "float", "min": 0.015, "max": 0.035, "step": 0.01},
        "min_pct_chg": {"type": "float", "min": 0.3, "max": 1.0, "step": 0.35},
        "min_signal_vol_ratio": {"type": "float", "min": 1.0, "max": 1.5, "step": 0.25},
    },
))

# ---------------------------------------------------------------------------
# 策略注册：V4 量价配合策略（1 种）
# ---------------------------------------------------------------------------
from app.strategy.technical.volume_price_pattern import VolumePricePatternStrategy  # noqa: E402

_register(StrategyMeta(
    name="volume-price-pattern",
    display_name="量价配合（龙回头）",
    category="technical",
    description="放量突破后缩量回踩企稳，捕捉主升浪启动点",
    strategy_cls=VolumePricePatternStrategy,
    default_params=VolumePricePatternStrategy.default_params,
    param_space={
        "accumulation_days": {"type": "int", "min": 30, "max": 60, "step": 15},
        "min_t0_pct_chg": {"type": "float", "min": 5.0, "max": 7.0, "step": 1.0},
        "min_t0_vol_ratio": {"type": "float", "min": 2.0, "max": 3.0, "step": 0.5},
        "min_washout_days": {"type": "int", "min": 2, "max": 4, "step": 1},
        "max_washout_days": {"type": "int", "min": 6, "max": 10, "step": 2},
        "max_vol_shrink_ratio": {"type": "float", "min": 0.30, "max": 0.50, "step": 0.10},
        "max_tk_amplitude": {"type": "float", "min": 2.0, "max": 4.0, "step": 1.0},
        "ma_support_tolerance": {"type": "float", "min": 0.010, "max": 0.020, "step": 0.005},
    },
))
