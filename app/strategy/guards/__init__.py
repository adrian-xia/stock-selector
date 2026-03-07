"""V2 Guard 策略：排雷卫兵。

Guard 输出布尔值（True=通过），以 AND 逻辑执行。
任一 guard 不通过则剔除该股票。
"""

from app.strategy.adapters.guard_adapter import GuardAdapter
from app.strategy.base import BaseStrategyV2, StrategyRole
from app.strategy.fundamental.cashflow_quality import CashflowQualityStrategy
from app.strategy.fundamental.financial_safety import FinancialSafetyStrategy


class FinancialSafetyGuardV2(BaseStrategyV2):
    """财务安全 Guard V2。"""

    name = "financial-safety-guard-v2"
    display_name = "财务安全（排雷）"
    role = StrategyRole.GUARD
    signal_group = None
    description = "资产负债率/流动比率/速动比率"
    default_params = FinancialSafetyStrategy.default_params
    ai_rating = 6.72

    def __init__(self, params: dict | None = None) -> None:
        """初始化 Guard。"""
        super().__init__(params)
        self._adapter = GuardAdapter(
            FinancialSafetyStrategy(self.params),
            ai_rating=self.ai_rating,
        )

    async def execute(self, df, target_date):
        """执行 Guard 策略。"""
        return await self._adapter.execute(df, target_date)


class CashflowQualityGuardV2(BaseStrategyV2):
    """现金流质量 Guard V2。"""

    name = "cashflow-quality-guard-v2"
    display_name = "现金流质量（排雷）"
    role = StrategyRole.GUARD
    signal_group = None
    description = "OCF/EPS>=1，排除纸面利润"
    default_params = CashflowQualityStrategy.default_params
    ai_rating = 7.33

    def __init__(self, params: dict | None = None) -> None:
        """初始化 Guard。"""
        super().__init__(params)
        self._adapter = GuardAdapter(
            CashflowQualityStrategy(self.params),
            ai_rating=self.ai_rating,
        )

    async def execute(self, df, target_date):
        """执行 Guard 策略。"""
        return await self._adapter.execute(df, target_date)


__all__ = [
    "FinancialSafetyGuardV2",
    "CashflowQualityGuardV2",
]
