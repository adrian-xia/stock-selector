"""策略工厂。

- `STRATEGY_REGISTRY_V2`：当前生产使用的 20 个 V2 策略
- `STRATEGY_REGISTRY`：仍在使用的遗留策略元数据（目前仅保留 V4 `volume-price-pattern`）
"""

from dataclasses import dataclass, field

from app.strategy.base import BaseStrategy, BaseStrategyV2, SignalGroup, StrategyRole


@dataclass(frozen=True)
class StrategyMeta:
    """仍在使用的遗留策略元数据。"""

    name: str
    display_name: str
    category: str
    description: str
    strategy_cls: type[BaseStrategy]
    default_params: dict = field(default_factory=dict)
    param_space: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyMetaV2:
    """V2 策略元数据。"""

    name: str
    display_name: str
    role: StrategyRole
    signal_group: SignalGroup | None
    description: str
    strategy_cls: type[BaseStrategyV2]
    ai_rating: float
    default_params: dict = field(default_factory=dict)
    param_space: dict = field(default_factory=dict)
    style_keys: list[str] = field(default_factory=list)


STRATEGY_REGISTRY: dict[str, StrategyMeta] = {}
STRATEGY_REGISTRY_V2: dict[str, StrategyMetaV2] = {}


def resolve_v2_default_params(meta: StrategyMetaV2) -> dict:
    """解析 V2 策略默认参数。"""
    if meta.default_params:
        return dict(meta.default_params)
    return dict(getattr(meta.strategy_cls, "default_params", {}) or {})


def build_v2_param_space(default_params: dict) -> dict:
    """基于默认参数生成简易参数空间。"""
    param_space: dict[str, dict] = {}
    for key, value in default_params.items():
        if isinstance(value, bool):
            param_space[key] = {"type": "bool"}
            continue

        if isinstance(value, int) and not isinstance(value, bool):
            step = 1 if value <= 10 else 2 if value <= 20 else 5
            param_space[key] = {
                "type": "int",
                "min": max(1, value - step * 2),
                "max": value + step * 2,
                "step": step,
            }
            continue

        if isinstance(value, float):
            step = 0.05 if value < 1 else 0.1 if value < 5 else 0.5
            param_space[key] = {
                "type": "float",
                "min": max(0.0, round(value - step * 2, 4)),
                "max": round(value + step * 2, 4),
                "step": step,
            }

    return param_space


class StrategyFactoryV2:
    """V2 策略工厂。"""

    @classmethod
    def get_strategy(
        cls,
        name: str,
        params: dict | None = None,
    ) -> BaseStrategyV2:
        if name not in STRATEGY_REGISTRY_V2:
            available = list(STRATEGY_REGISTRY_V2.keys())
            raise KeyError(f"V2 策略 '{name}' 未注册，可用策略：{available}")

        meta = STRATEGY_REGISTRY_V2[name]
        strategy = meta.strategy_cls(params=params)
        strategy.name = meta.name
        strategy.display_name = meta.display_name
        strategy.role = meta.role
        strategy.signal_group = meta.signal_group
        strategy.description = meta.description
        strategy.default_params = resolve_v2_default_params(meta)
        strategy.ai_rating = meta.ai_rating
        strategy.params = {**strategy.default_params, **(params or {})}
        return strategy

    @classmethod
    def get_all(cls) -> list[StrategyMetaV2]:
        return list(STRATEGY_REGISTRY_V2.values())

    @classmethod
    def get_by_role(cls, role: StrategyRole) -> list[StrategyMetaV2]:
        return [meta for meta in STRATEGY_REGISTRY_V2.values() if meta.role == role]

    @classmethod
    def get_by_signal_group(cls, signal_group: SignalGroup) -> list[StrategyMetaV2]:
        return [
            meta
            for meta in STRATEGY_REGISTRY_V2.values()
            if meta.role == StrategyRole.TRIGGER and meta.signal_group == signal_group
        ]

    @classmethod
    def get_meta(cls, name: str) -> StrategyMetaV2:
        if name not in STRATEGY_REGISTRY_V2:
            available = list(STRATEGY_REGISTRY_V2.keys())
            raise KeyError(f"V2 策略 '{name}' 未注册，可用策略：{available}")
        return STRATEGY_REGISTRY_V2[name]


def _register(meta: StrategyMeta) -> None:
    STRATEGY_REGISTRY[meta.name] = meta


def _register_v2(meta: StrategyMetaV2) -> None:
    STRATEGY_REGISTRY_V2[meta.name] = meta


# ---------------------------------------------------------------------------
# V2 策略注册：20 个策略
# ---------------------------------------------------------------------------

from app.strategy.confirmers.bias_extreme_v2 import BIASExtremeConfirmerV2  # noqa: E402
from app.strategy.confirmers.ma_long_arrange_v2 import MALongArrangeConfirmerV2  # noqa: E402
from app.strategy.confirmers.macd_divergence_v2 import MACDDivergenceConfirmerV2  # noqa: E402
from app.strategy.confirmers.rsi_oversold_v2 import RSIOversoldConfirmerV2  # noqa: E402
from app.strategy.confirmers.shrink_volume_rise_v2 import ShrinkVolumeRiseConfirmerV2  # noqa: E402
from app.strategy.guards import CashflowQualityGuardV2, FinancialSafetyGuardV2  # noqa: E402
from app.strategy.scorers.quality_score_v2 import QualityScoreStrategyV2  # noqa: E402
from app.strategy.taggers import HighDividendTaggerV2, LowPEHighROETaggerV2  # noqa: E402
from app.strategy.triggers import (  # noqa: E402
    ATRBreakoutTriggerV2,
    DragonTurnaroundTriggerV2,
    ExtremeShrinkBottomTriggerV2,
    FirstNegativeReversalTriggerV2,
    PeakPullbackStabilizationTriggerV2,
    PullbackHalfRuleTriggerV2,
    VolumeBreakoutTriggerV2,
    VolumeContractionPullbackTriggerV2,
    VolumePriceStableTriggerV2,
    VolumeSurgeContinuationTriggerV2,
)

_register_v2(StrategyMetaV2(
    name="quality-score-v2",
    display_name="综合质量评分",
    role=StrategyRole.SCORER,
    signal_group=None,
    description="ROE+成长+安全+估值+毛利率变化，行业中性化Z-Score",
    strategy_cls=QualityScoreStrategyV2,
    ai_rating=7.80,
))

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
    ai_rating=5.58,
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
    ai_rating=7.13,
))
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
    ai_rating=7.85,
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
# 遗留活跃策略：仅保留仍在使用的 V4 量价配合
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
