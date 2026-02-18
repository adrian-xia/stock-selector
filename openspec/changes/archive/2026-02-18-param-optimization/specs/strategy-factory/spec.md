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
- `param_space: dict` — optimizable parameter ranges (optional, default empty dict)

The `param_space` format for each parameter:
```
{"param_name": {"type": "int"|"float", "min": N, "max": N, "step": N}}
```

#### Scenario: Registry contains all strategies
- **WHEN** `StrategyFactory.get_all()` is called
- **THEN** it SHALL return a list of 28 `StrategyMeta` entries (16 technical + 12 fundamental)

#### Scenario: Get param space for strategy
- **WHEN** `StrategyFactory.get_meta("ma-cross")` is called
- **THEN** the returned `StrategyMeta` SHALL include a non-empty `param_space` dict
