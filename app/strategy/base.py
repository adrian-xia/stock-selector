"""策略基类定义。

所有选股策略直接继承 BaseStrategy（V1 扁平继承），
通过 category 属性区分技术面/基本面。
"""

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class BaseStrategy(ABC):
    """选股策略抽象基类。

    所有策略必须继承此类并实现 filter_batch 方法。
    V1 采用扁平继承，不设中间抽象子类。

    Attributes:
        name: 策略唯一标识（kebab-case），如 "ma-cross"
        display_name: 人类可读名称，如 "均线金叉"
        category: 策略分类，"technical" 或 "fundamental"
        description: 策略逻辑的一句话描述
        default_params: 默认参数字典
        params: 运行时参数（default_params 与自定义参数合并后的结果）
    """

    # 子类必须覆盖以下类属性
    name: str = ""
    display_name: str = ""
    category: str = ""  # "technical" 或 "fundamental"
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
        """批量筛选股票。

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
