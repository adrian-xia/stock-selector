## ADDED Requirements

### Requirement: StrategyFactory registry
The system SHALL provide a `StrategyFactory` class that maintains a registry of all available strategies using a manual dictionary mapping.

The registry SHALL map strategy `name` (str) to a `StrategyMeta` dataclass containing:
- `name: str` — unique identifier
- `display_name: str` — human-readable name
- `category: str` — `"technical"` or `"fundamental"`
- `description: str` — one-sentence description
- `strategy_cls: type[BaseStrategy]` — the strategy class reference
- `default_params: dict` — default parameter values

#### Scenario: Registry contains all V1 strategies
- **WHEN** `StrategyFactory.get_all()` is called
- **THEN** it SHALL return a list of 12 `StrategyMeta` entries (8 technical + 4 fundamental)

### Requirement: StrategyFactory.get_strategy instantiation
The `StrategyFactory` SHALL provide a `get_strategy(name, params=None)` class method that instantiates a strategy by name.

#### Scenario: Get strategy by name
- **WHEN** `StrategyFactory.get_strategy("ma-cross")` is called
- **THEN** it SHALL return a `MACrossStrategy` instance with default params

#### Scenario: Get strategy with custom params
- **WHEN** `StrategyFactory.get_strategy("ma-cross", params={"fast": 10})` is called
- **THEN** it SHALL return a `MACrossStrategy` instance with `params["fast"] == 10`

#### Scenario: Get unknown strategy
- **WHEN** `StrategyFactory.get_strategy("nonexistent")` is called
- **THEN** it SHALL raise `KeyError` with a message listing available strategy names

### Requirement: StrategyFactory.get_by_category filtering
The `StrategyFactory` SHALL provide a `get_by_category(category)` class method.

#### Scenario: Filter technical strategies
- **WHEN** `StrategyFactory.get_by_category("technical")` is called
- **THEN** it SHALL return a list of 8 `StrategyMeta` entries (all technical strategies)

#### Scenario: Filter fundamental strategies
- **WHEN** `StrategyFactory.get_by_category("fundamental")` is called
- **THEN** it SHALL return a list of 4 `StrategyMeta` entries

### Requirement: StrategyFactory.get_meta metadata query
The `StrategyFactory` SHALL provide a `get_meta(name)` class method that returns the `StrategyMeta` for a given strategy name.

#### Scenario: Get strategy metadata
- **WHEN** `StrategyFactory.get_meta("ma-cross")` is called
- **THEN** it SHALL return a `StrategyMeta` with `name="ma-cross"`, `display_name="均线金叉"`, `category="technical"`
