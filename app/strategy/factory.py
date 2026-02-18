"""策略工厂：注册、查询和实例化策略。

V1 使用手动字典注册，所有策略在模块底部显式注册。
"""

from dataclasses import dataclass, field

from app.strategy.base import BaseStrategy


@dataclass(frozen=True)
class StrategyMeta:
    """策略元数据，描述一个策略的静态信息。"""

    name: str                          # 唯一标识，如 "ma-cross"
    display_name: str                  # 显示名称，如 "均线金叉"
    category: str                      # "technical" 或 "fundamental"
    description: str                   # 一句话描述
    strategy_cls: type[BaseStrategy]   # 策略类引用
    default_params: dict = field(default_factory=dict)
    param_space: dict = field(default_factory=dict)  # 可优化参数空间


# 策略注册表：name -> StrategyMeta
STRATEGY_REGISTRY: dict[str, StrategyMeta] = {}


class StrategyFactory:
    """策略工厂，提供策略的查询和实例化能力。"""

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


def _register(meta: StrategyMeta) -> None:
    """内部注册函数，将策略元数据写入注册表。"""
    STRATEGY_REGISTRY[meta.name] = meta


# ---------------------------------------------------------------------------
# 策略注册：技术面（16 种）
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
