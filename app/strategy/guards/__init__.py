"""V2 Guard 策略：排雷卫兵。

Guard 输出布尔值（True=通过），以 AND 逻辑执行。
任一 guard 不通过则剔除该股票。
"""

from app.strategy.adapters.guard_adapter import GuardAdapter
from app.strategy.base import BaseStrategyV2
from app.strategy.fundamental.cashflow_quality import CashflowQualityStrategy
from app.strategy.fundamental.financial_safety import FinancialSafetyStrategy


class FinancialSafetyGuardV2(BaseStrategyV2):
    """财务安全 Guard V2。"""

    def __init__(self, params: dict | None = None) -> None:
        """初始化 Guard。"""
        self._adapter = GuardAdapter(FinancialSafetyStrategy(params), ai_rating=6.20)
        # 复制适配器的属性
        self.name = self._adapter.name
        self.display_name = self._adapter.display_name
        self.role = self._adapter.role
        self.signal_group = self._adapter.signal_group
        self.description = self._adapter.description
        self.default_params = self._adapter.default_params
        self.ai_rating = self._adapter.ai_rating
        self.params = self._adapter.params

    async def execute(self, df, target_date):
        """执行 Guard 策略。"""
        return await self._adapter.execute(df, target_date)


class CashflowQualityGuardV2(BaseStrategyV2):
    """现金流质量 Guard V2。"""

    def __init__(self, params: dict | None = None) -> None:
        """初始化 Guard。"""
        self._adapter = GuardAdapter(CashflowQualityStrategy(params), ai_rating=5.87)
        # 复制适配器的属性
        self.name = self._adapter.name
        self.display_name = self._adapter.display_name
        self.role = self._adapter.role
        self.signal_group = self._adapter.signal_group
        self.description = self._adapter.description
        self.default_params = self._adapter.default_params
        self.ai_rating = self._adapter.ai_rating
        self.params = self._adapter.params

    async def execute(self, df, target_date):
        """执行 Guard 策略。"""
        return await self._adapter.execute(df, target_date)


__all__ = [
    "FinancialSafetyGuardV2",
    "CashflowQualityGuardV2",
]
