"""参数优化模块。

提供网格搜索和遗传算法两种优化器，自动寻找策略最优参数组合。
"""

from app.optimization.base import BaseOptimizer, OptimizationResult
from app.optimization.genetic import GeneticOptimizer
from app.optimization.grid_search import GridSearchOptimizer
from app.optimization.param_space import count_combinations, generate_combinations

__all__ = [
    "BaseOptimizer",
    "OptimizationResult",
    "GridSearchOptimizer",
    "GeneticOptimizer",
    "generate_combinations",
    "count_combinations",
]
