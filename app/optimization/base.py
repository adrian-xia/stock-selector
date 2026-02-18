"""优化器基类和结果数据类。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker


@dataclass
class OptimizationResult:
    """单次参数组合的优化结果。"""

    params: dict = field(default_factory=dict)
    sharpe_ratio: float | None = None
    annual_return: float | None = None
    max_drawdown: float | None = None
    win_rate: float | None = None
    total_trades: int = 0
    total_return: float | None = None
    volatility: float | None = None
    calmar_ratio: float | None = None
    sortino_ratio: float | None = None


# 进度回调类型：(completed, total) -> None
ProgressCallback = Callable[[int, int], Any]


class BaseOptimizer(ABC):
    """优化器抽象基类。"""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    @abstractmethod
    async def optimize(
        self,
        strategy_name: str,
        param_space: dict,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        initial_capital: float = 1_000_000.0,
        progress_callback: ProgressCallback | None = None,
    ) -> list[OptimizationResult]:
        """执行参数优化，返回按 sharpe_ratio 降序排列的结果列表。

        Args:
            strategy_name: 策略名称
            param_space: 参数空间定义
            stock_codes: 回测股票代码列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_capital: 初始资金
            progress_callback: 进度回调函数

        Returns:
            按 sharpe_ratio 降序排列的 OptimizationResult 列表
        """
        ...
