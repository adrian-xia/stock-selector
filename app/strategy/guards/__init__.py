"""V2 Guard 策略：排雷卫兵。

Guard 输出布尔值（True=通过），以 AND 逻辑执行。
任一 guard 不通过则剔除该股票。
"""

from functools import partial

from app.strategy.adapters.guard_adapter import GuardAdapter
from app.strategy.fundamental.cashflow_quality import CashflowQualityStrategy
from app.strategy.fundamental.financial_safety import FinancialSafetyStrategy


def _make_financial_safety_guard(params=None):
    """工厂函数：创建财务安全 Guard 实例。"""
    return GuardAdapter(FinancialSafetyStrategy(params), ai_rating=6.20)


def _make_cashflow_quality_guard(params=None):
    """工厂函数：创建现金流质量 Guard 实例。"""
    return GuardAdapter(CashflowQualityStrategy(params), ai_rating=5.87)


# 导出类（用于注册）
FinancialSafetyGuardV2 = type(
    "FinancialSafetyGuardV2",
    (),
    {"__call__": staticmethod(_make_financial_safety_guard)},
)

CashflowQualityGuardV2 = type(
    "CashflowQualityGuardV2",
    (),
    {"__call__": staticmethod(_make_cashflow_quality_guard)},
)

__all__ = [
    "FinancialSafetyGuardV2",
    "CashflowQualityGuardV2",
]
