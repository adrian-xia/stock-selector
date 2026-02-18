## ADDED Requirements

### Requirement: BaseOptimizer interface
The system SHALL provide a `BaseOptimizer` abstract base class in `app/optimization/base.py` with an async `optimize()` method.

The `optimize()` method SHALL accept:
- `strategy_name: str`
- `param_space: dict` — parameter ranges
- `stock_codes: list[str]`
- `start_date: date`
- `end_date: date`
- `initial_capital: float`

And SHALL return a list of `OptimizationResult` dataclass instances sorted by `sharpe_ratio` descending.

#### Scenario: Optimizer returns sorted results
- **WHEN** `optimize()` completes
- **THEN** results SHALL be sorted by sharpe_ratio descending, each containing params, sharpe_ratio, annual_return, max_drawdown, win_rate, total_trades, total_return, volatility

### Requirement: GridSearchOptimizer
The system SHALL provide a `GridSearchOptimizer` that exhaustively evaluates all parameter combinations in the given param_space.

Parameter space format:
```
{"param_name": {"type": "int"|"float", "min": N, "max": N, "step": N}}
```

The optimizer SHALL generate all combinations from the cartesian product of parameter ranges, execute a backtest for each combination via `BacktestEngine.run()`, and collect results.

#### Scenario: Grid search with 2 parameters
- **WHEN** param_space is `{"fast": {"type": "int", "min": 3, "max": 5, "step": 1}, "slow": {"type": "int", "min": 10, "max": 20, "step": 5}}`
- **THEN** optimizer SHALL evaluate 3 × 3 = 9 combinations

#### Scenario: Grid search reports progress
- **WHEN** grid search is running
- **THEN** it SHALL update progress (completed_combinations / total_combinations) via a callback

### Requirement: GeneticOptimizer
The system SHALL provide a `GeneticOptimizer` that uses a genetic algorithm to search the parameter space efficiently.

Default GA config: `{"population_size": 20, "max_generations": 50, "crossover_rate": 0.8, "mutation_rate": 0.1, "tournament_size": 3}`

The fitness function SHALL be the sharpe_ratio from backtest results.

#### Scenario: Genetic algorithm converges
- **WHEN** `GeneticOptimizer.optimize()` is called with default config
- **THEN** it SHALL run up to 50 generations with population size 20, using tournament selection, crossover, and mutation

#### Scenario: GA respects parameter bounds
- **WHEN** mutation or crossover produces a parameter value outside the defined range
- **THEN** the value SHALL be clamped to [min, max]

#### Scenario: GA reports progress
- **WHEN** genetic algorithm is running
- **THEN** it SHALL update progress (current_generation / max_generations) via a callback

### Requirement: Parameter space generation
The system SHALL provide a `generate_combinations(param_space: dict) -> list[dict]` utility function that generates all parameter combinations from a param_space definition.

#### Scenario: Generate int combinations
- **WHEN** param_space is `{"period": {"type": "int", "min": 5, "max": 15, "step": 5}}`
- **THEN** it SHALL return `[{"period": 5}, {"period": 10}, {"period": 15}]`

#### Scenario: Generate float combinations
- **WHEN** param_space is `{"ratio": {"type": "float", "min": 1.0, "max": 2.0, "step": 0.5}}`
- **THEN** it SHALL return `[{"ratio": 1.0}, {"ratio": 1.5}, {"ratio": 2.0}]`
