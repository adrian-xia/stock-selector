## MODIFIED Requirements

### Requirement: StrategyFactory registry
The system SHALL provide a `StrategyFactory` class that maintains a registry of all available strategies using a manual dictionary mapping.

The registry SHALL map strategy `name` (str) to a `StrategyMeta` dataclass containing:
- `name: str` — unique identifier
- `display_name: str` — human-readable name
- `category: str` — `"technical"` or `"fundamental"`
- `description: str` — one-sentence description
- `strategy_cls: type[BaseStrategy]` — the strategy class reference
- `default_params: dict` — default parameter values

#### Scenario: Registry contains all strategies
- **WHEN** `StrategyFactory.get_all()` is called
- **THEN** it SHALL return a list of 20 `StrategyMeta` entries (16 technical + 4 fundamental)

### Requirement: StrategyFactory.get_by_category filtering
The `StrategyFactory` SHALL provide a `get_by_category(category)` class method.

#### Scenario: Filter technical strategies
- **WHEN** `StrategyFactory.get_by_category("technical")` is called
- **THEN** it SHALL return a list of 16 `StrategyMeta` entries (all technical strategies)

#### Scenario: Filter fundamental strategies
- **WHEN** `StrategyFactory.get_by_category("fundamental")` is called
- **THEN** it SHALL return a list of 4 `StrategyMeta` entries
