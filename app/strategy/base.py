"""策略基类定义。

V1: 扁平继承，通过 category 属性区分技术面/基本面
V2: 角色分层，通过 role 属性区分 guard/scorer/tagger/trigger/confirmer
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

import pandas as pd


# ============================================================================
# V2 新增：策略角色枚举
# ============================================================================


class StrategyRole(str, Enum):
    """策略角色（V2）。"""

    GUARD = "guard"  # 排雷卫兵：硬性排除
    SCORER = "scorer"  # 质量评分：输出连续分数
    TAGGER = "tagger"  # 风格标签：打标签
    TRIGGER = "trigger"  # 信号触发：核心选股信号
    CONFIRMER = "confirmer"  # 辅助确认：为已有信号加分


class SignalGroup(str, Enum):
    """信号分组（仅 trigger 角色使用）。"""

    AGGRESSIVE = "aggressive"  # 进攻组
    TREND = "trend"  # 趋势组
    BOTTOM = "bottom"  # 底部组


@dataclass
class StrategySignal:
    """策略输出的信号（V2）。"""

    ts_code: str
    confidence: float = 1.0  # 信号置信度 0.0-1.0


# ============================================================================
# V1 BaseStrategy（保留向后兼容）
# ============================================================================


class BaseStrategy(ABC):
    """选股策略抽象基类（V1）。

    所有策略必须继承此类并实现 filter_batch 方法。
    V1 采用扁平继承，不设中间抽象子类。

    Attributes:
        name: 策略唯一标识（kebab-case），如 "ma-cross"
        display_name: 人类可读名称，如 "均线金叉"
        category: 策略分类，"technical" 或 "fundamental"（V1）
        description: 策略逻辑的一句话描述
        default_params: 默认参数字典
        params: 运行时参数（default_params 与自定义参数合并后的结果）
    """

    # 子类必须覆盖以下类属性
    name: str = ""
    display_name: str = ""
    category: str = ""  # "technical" 或 "fundamental"（V1）
    description: str = ""
    default_params: dict = {}

    def __init__(self, params: dict | None = None) -> None:
        """初始化策略实例。

        Args:
            params: 自定义参数，会覆盖 default_params 中的同名键
        """
        # 合并参数：default_params 为底，自定义 params 覆盖
        self.params = {**self.default_params}
        if params:
            self.params.update(params)

    @abstractmethod
    async def filter_batch(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> pd.Series:
        """批量筛选股票（V1 接口）。

        对全市场数据执行向量化筛选，返回布尔 Series。

        Args:
            df: 全市场行情 DataFrame，每行一只股票当日数据。
                列包含 stock_daily 字段（ts_code, close, vol 等）、
                technical_daily 字段（ma5, rsi6 等）、
                前日指标（ma5_prev 等）和 finance_indicator 字段。
            target_date: 筛选日期

        Returns:
            与 df 等长的布尔 Series，True 表示通过筛选
        """
        ...


# ============================================================================
# V2 BaseStrategyV2（新架构）
# ============================================================================


class BaseStrategyV2(ABC):
    """策略基类（V2 重设计）。

    V2 引入角色分层：guard/scorer/tagger/trigger/confirmer。
    不同角色的 execute 方法返回值类型不同。
    """

    name: str = ""
    display_name: str = ""
    role: StrategyRole = StrategyRole.TRIGGER
    signal_group: SignalGroup | None = None  # 仅 trigger 有
    description: str = ""
    default_params: dict = {}
    # 三模型综合均分（用于静态权重计算）
    ai_rating: float = 5.0

    def __init__(self, params: dict | None = None) -> None:
        self.params = {**self.default_params}
        if params:
            self.params.update(params)

    @abstractmethod
    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> list[StrategySignal] | pd.Series | dict[str, float]:
        """执行策略（V2 接口）。

        根据角色不同，返回值不同：
        - guard: pd.Series[bool]（True=通过）
        - scorer: pd.Series[float]（0-100 连续分数）
        - tagger: dict[str, pd.Series[float]]（风格标签 -> 强度 Series，0.0-1.0）
        - trigger: list[StrategySignal]（命中信号列表，含置信度）
        - confirmer: pd.Series[float]（加分系数 0.0-1.0）
        """
        ...

    @property
    def static_weight(self) -> float:
        """基于三模型均分的静态权重（归一化到 0-1）。"""
        return self.ai_rating / 8.32  # 除以最高分归一化


# ============================================================================
# V2 策略元数据
# ============================================================================


@dataclass(frozen=True)
class StrategyMeta:
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
