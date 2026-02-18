"""遗传算法优化器：高效搜索大参数空间。"""

import logging
import random
from datetime import date
from typing import Any

from app.backtest.engine import run_backtest
from app.optimization.base import BaseOptimizer, OptimizationResult, ProgressCallback
from app.optimization.grid_search import _extract_result

logger = logging.getLogger(__name__)

# 默认遗传算法超参数
DEFAULT_GA_CONFIG = {
    "population_size": 20,
    "max_generations": 50,
    "crossover_rate": 0.8,
    "mutation_rate": 0.1,
    "tournament_size": 3,
}


class GeneticOptimizer(BaseOptimizer):
    """遗传算法优化器。

    使用锦标赛选择、单点交叉和随机变异搜索参数空间，
    适应度函数为 sharpe_ratio。
    """

    async def optimize(
        self,
        strategy_name: str,
        param_space: dict,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        initial_capital: float = 1_000_000.0,
        progress_callback: ProgressCallback | None = None,
        ga_config: dict | None = None,
    ) -> list[OptimizationResult]:
        """执行遗传算法优化。"""
        config = {**DEFAULT_GA_CONFIG, **(ga_config or {})}
        pop_size = config["population_size"]
        max_gen = config["max_generations"]
        crossover_rate = config["crossover_rate"]
        mutation_rate = config["mutation_rate"]
        tournament_size = config["tournament_size"]

        param_names = list(param_space.keys())
        logger.info(
            "遗传算法开始：策略=%s，种群=%d，代数=%d",
            strategy_name, pop_size, max_gen,
        )

        # 初始化种群
        population = [_random_individual(param_space) for _ in range(pop_size)]

        # 记录所有评估过的结果（去重）
        all_results: dict[str, OptimizationResult] = {}

        for gen in range(max_gen):
            # 评估适应度
            fitness_scores: list[tuple[dict, float]] = []
            for individual in population:
                key = _individual_key(individual)
                if key not in all_results:
                    result = await self._evaluate(
                        strategy_name, individual, stock_codes,
                        start_date, end_date, initial_capital,
                    )
                    all_results[key] = result

                cached = all_results[key]
                fitness = cached.sharpe_ratio if cached.sharpe_ratio is not None else float("-inf")
                fitness_scores.append((individual, fitness))

            # 选择 + 交叉 + 变异 → 新种群
            new_population: list[dict] = []
            while len(new_population) < pop_size:
                # 锦标赛选择
                parent1 = _tournament_select(fitness_scores, tournament_size)
                parent2 = _tournament_select(fitness_scores, tournament_size)

                # 交叉
                if random.random() < crossover_rate:
                    child1, child2 = _crossover(parent1, parent2, param_names)
                else:
                    child1, child2 = parent1.copy(), parent2.copy()

                # 变异
                child1 = _mutate(child1, param_space, mutation_rate)
                child2 = _mutate(child2, param_space, mutation_rate)

                new_population.append(child1)
                if len(new_population) < pop_size:
                    new_population.append(child2)

            population = new_population

            if progress_callback:
                progress_callback(gen + 1, max_gen)

            # 日志：当代最优
            best_fitness = max(f for _, f in fitness_scores)
            logger.debug("第 %d 代完成，最优适应度: %.4f", gen + 1, best_fitness)

        # 返回所有结果按 sharpe_ratio 降序
        results = list(all_results.values())
        results.sort(
            key=lambda r: r.sharpe_ratio if r.sharpe_ratio is not None else float("-inf"),
            reverse=True,
        )

        logger.info("遗传算法完成：共评估 %d 个不同参数组合", len(results))
        return results

    async def _evaluate(
        self,
        strategy_name: str,
        params: dict,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        initial_capital: float,
    ) -> OptimizationResult:
        """评估单个参数组合。"""
        try:
            bt_result = await run_backtest(
                session_factory=self._session_factory,
                stock_codes=stock_codes,
                strategy_name=strategy_name,
                strategy_params=params,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
            )
            return _extract_result(params, bt_result)
        except Exception:
            logger.warning("参数组合 %s 回测失败", params, exc_info=True)
            return OptimizationResult(params=params)


def _random_individual(param_space: dict) -> dict:
    """生成随机个体。"""
    individual = {}
    for name, spec in param_space.items():
        min_val = spec["min"]
        max_val = spec["max"]
        step = spec["step"]
        # 在合法步长点中随机选择
        import math
        n_steps = math.floor((max_val - min_val) / step)
        chosen_step = random.randint(0, n_steps)
        val = min_val + chosen_step * step
        if spec["type"] == "int":
            individual[name] = int(round(val))
        else:
            individual[name] = round(val, 6)
    return individual


def _individual_key(individual: dict) -> str:
    """生成个体的唯一键（用于去重缓存）。"""
    return str(sorted(individual.items()))


def _tournament_select(
    fitness_scores: list[tuple[dict, float]],
    tournament_size: int,
) -> dict:
    """锦标赛选择：随机选 tournament_size 个，取最优。"""
    candidates = random.sample(fitness_scores, min(tournament_size, len(fitness_scores)))
    winner = max(candidates, key=lambda x: x[1])
    return winner[0].copy()


def _crossover(
    parent1: dict,
    parent2: dict,
    param_names: list[str],
) -> tuple[dict, dict]:
    """单点交叉。"""
    if len(param_names) <= 1:
        return parent1.copy(), parent2.copy()

    point = random.randint(1, len(param_names) - 1)
    child1 = {}
    child2 = {}
    for i, name in enumerate(param_names):
        if i < point:
            child1[name] = parent1[name]
            child2[name] = parent2[name]
        else:
            child1[name] = parent2[name]
            child2[name] = parent1[name]
    return child1, child2


def _mutate(individual: dict, param_space: dict, mutation_rate: float) -> dict:
    """随机变异：每个参数以 mutation_rate 概率随机重置。"""
    import math
    mutated = individual.copy()
    for name, spec in param_space.items():
        if random.random() < mutation_rate:
            min_val = spec["min"]
            max_val = spec["max"]
            step = spec["step"]
            n_steps = math.floor((max_val - min_val) / step)
            chosen_step = random.randint(0, n_steps)
            val = min_val + chosen_step * step
            if spec["type"] == "int":
                mutated[name] = int(round(val))
            else:
                mutated[name] = round(val, 6)
    return mutated
