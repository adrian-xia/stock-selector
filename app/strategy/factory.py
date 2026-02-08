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
# 策略注册：技术面（8 种）
# ---------------------------------------------------------------------------
from app.strategy.technical.ma_cross import MACrossStrategy  # noqa: E402
from app.strategy.technical.macd_golden import MACDGoldenStrategy  # noqa: E402
from app.strategy.technical.rsi_oversold import RSIOversoldStrategy  # noqa: E402
from app.strategy.technical.kdj_golden import KDJGoldenStrategy  # noqa: E402
from app.strategy.technical.boll_breakthrough import BollBreakthroughStrategy  # noqa: E402
from app.strategy.technical.volume_breakout import VolumeBreakoutStrategy  # noqa: E402
from app.strategy.technical.ma_long_arrange import MALongArrangeStrategy  # noqa: E402
from app.strategy.technical.macd_divergence import MACDDivergenceStrategy  # noqa: E402

# ---------------------------------------------------------------------------
# 策略注册：基本面（4 种）
# ---------------------------------------------------------------------------
from app.strategy.fundamental.low_pe_high_roe import LowPEHighROEStrategy  # noqa: E402
from app.strategy.fundamental.high_dividend import HighDividendStrategy  # noqa: E402
from app.strategy.fundamental.growth_stock import GrowthStockStrategy  # noqa: E402
from app.strategy.fundamental.financial_safety import FinancialSafetyStrategy  # noqa: E402

# --- 技术面策略注册 ---
_register(StrategyMeta(
    name="ma-cross",
    display_name="均线金叉",
    category="technical",
    description="短期均线上穿长期均线，且成交量放大",
    strategy_cls=MACrossStrategy,
    default_params={"fast": 5, "slow": 10, "vol_ratio": 1.5},
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
))
_register(StrategyMeta(
    name="kdj-golden",
    display_name="KDJ金叉",
    category="technical",
    description="KDJ K线上穿D线，且J值处于超卖区域",
    strategy_cls=KDJGoldenStrategy,
    default_params={"oversold_j": 20},
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
))

# --- 基本面策略注册 ---
_register(StrategyMeta(
    name="low-pe-high-roe",
    display_name="低估值高成长",
    category="fundamental",
    description="市盈率低于30，ROE高于15%，利润同比增长超20%",
    strategy_cls=LowPEHighROEStrategy,
    default_params={"pe_max": 30, "roe_min": 15, "profit_growth_min": 20},
))
_register(StrategyMeta(
    name="high-dividend",
    display_name="高股息",
    category="fundamental",
    description="股息率高于3%，市盈率低于20",
    strategy_cls=HighDividendStrategy,
    default_params={"min_dividend_yield": 3.0, "pe_max": 20},
))
_register(StrategyMeta(
    name="growth-stock",
    display_name="成长股",
    category="fundamental",
    description="营收和利润同比增长均超过20%",
    strategy_cls=GrowthStockStrategy,
    default_params={"revenue_growth_min": 20, "profit_growth_min": 20},
))
_register(StrategyMeta(
    name="financial-safety",
    display_name="财务安全",
    category="fundamental",
    description="资产负债率低于60%，流动比率高于1.5",
    strategy_cls=FinancialSafetyStrategy,
    default_params={"debt_ratio_max": 60, "current_ratio_min": 1.5},
))
