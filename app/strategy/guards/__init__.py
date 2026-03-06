"""V2 Guard 策略：排雷卫兵。

Guard 输出布尔值（True=通过），以 AND 逻辑执行。
任一 guard 不通过则剔除该股票。
"""

from app.strategy.adapters.guard_adapter import GuardAdapter
from app.strategy.fundamental.cashflow_quality import CashflowQualityStrategy
from app.strategy.fundamental.financial_safety import FinancialSafetyStrategy

# 使用 GuardAdapter 包装 V1 基本面策略为 V2 Guard
FinancialSafetyGuardV2 = GuardAdapter(
    FinancialSafetyStrategy(),
    ai_rating=6.20,  # 三模型均分
)

CashflowQualityGuardV2 = GuardAdapter(
    CashflowQualityStrategy(),
    ai_rating=5.87,  # 三模型均分
)

__all__ = [
    "FinancialSafetyGuardV2",
    "CashflowQualityGuardV2",
]
