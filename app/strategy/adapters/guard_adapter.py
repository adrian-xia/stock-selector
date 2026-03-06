"""Guard 适配器：将 V1 BaseStrategy 适配为 V2 Guard 角色。

Guard 策略返回 pd.Series[bool]，True 表示通过排雷检查。
可以直接复用 V1 的 filter_batch 方法。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy, BaseStrategyV2, StrategyRole


class GuardAdapter(BaseStrategyV2):
    """Guard 适配器：包装 V1 策略为 V2 Guard。

    使用方式：
        v1_strategy = FinancialSafetyStrategy()
        v2_guard = GuardAdapter(v1_strategy, ai_rating=6.72)
    """

    def __init__(self, v1_strategy: BaseStrategy, ai_rating: float = 5.0) -> None:
        """初始化适配器。

        Args:
            v1_strategy: V1 策略实例
            ai_rating: 三模型综合均分
        """
        self.v1_strategy = v1_strategy
        self.name = v1_strategy.name
        self.display_name = v1_strategy.display_name
        self.role = StrategyRole.GUARD
        self.signal_group = None
        self.description = v1_strategy.description
        self.default_params = v1_strategy.default_params
        self.ai_rating = ai_rating
        self.params = v1_strategy.params

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> pd.Series:
        """执行 Guard 策略。

        Returns:
            pd.Series[bool]，True 表示通过排雷检查
        """
        return await self.v1_strategy.filter_batch(df, target_date)
