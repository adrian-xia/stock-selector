## ADDED Requirements

### Requirement: POST /api/v1/strategy/run endpoint
The system SHALL provide a `POST /api/v1/strategy/run` endpoint that accepts a strategy execution request and returns results synchronously.

Request body:
```json
{
  "strategy_names": ["ma-cross", "low-pe-high-roe"],
  "target_date": "2026-02-07",
  "base_filter": {"exclude_st": true, "min_turnover_rate": 0.001},
  "top_n": 30
}
```

- `strategy_names`: list of strategy name identifiers (required, at least one)
- `target_date`: screening date in ISO format (optional, defaults to latest trading day)
- `base_filter`: Layer 1 filter overrides (optional)
- `top_n`: maximum number of results (optional, default 30)

Response body:
```json
{
  "target_date": "2026-02-07",
  "total_picks": 25,
  "elapsed_ms": 3200,
  "layer_stats": {"layer1": 4000, "layer2": 500, "layer3": 100, "layer4": 25},
  "picks": [
    {
      "ts_code": "600519.SH",
      "name": "贵州茅台",
      "close": 1705.20,
      "pct_chg": 1.25,
      "matched_strategies": ["ma-cross", "low-pe-high-roe"],
      "match_count": 2
    }
  ]
}
```

#### Scenario: Successful strategy execution
- **WHEN** `POST /api/v1/strategy/run` is called with valid strategy names
- **THEN** it SHALL return HTTP 200 with the pipeline result

#### Scenario: Invalid strategy name
- **WHEN** `POST /api/v1/strategy/run` is called with `strategy_names: ["nonexistent"]`
- **THEN** it SHALL return HTTP 400 with an error message listing available strategies

#### Scenario: Empty strategy list
- **WHEN** `POST /api/v1/strategy/run` is called with `strategy_names: []`
- **THEN** it SHALL return HTTP 422 validation error

### Requirement: GET /api/v1/strategy/list endpoint
The system SHALL provide a `GET /api/v1/strategy/list` endpoint that returns all available strategies with their metadata.

Query params:
- `category` (optional): filter by `"technical"` or `"fundamental"`

Response body:
```json
{
  "strategies": [
    {
      "name": "ma-cross",
      "display_name": "均线金叉",
      "category": "technical",
      "description": "短期均线上穿长期均线，且成交量放大",
      "default_params": {"fast": 5, "slow": 10, "vol_ratio": 1.5}
    }
  ]
}
```

#### Scenario: List all strategies
- **WHEN** `GET /api/v1/strategy/list` is called without params
- **THEN** it SHALL return all 12 registered strategies

#### Scenario: Filter by category
- **WHEN** `GET /api/v1/strategy/list?category=technical` is called
- **THEN** it SHALL return only the 8 technical strategies

### Requirement: GET /api/v1/strategy/schema/{name} endpoint
The system SHALL provide a `GET /api/v1/strategy/schema/{name}` endpoint that returns the parameter schema for a specific strategy.

Response body:
```json
{
  "name": "ma-cross",
  "display_name": "均线金叉",
  "default_params": {"fast": 5, "slow": 10, "vol_ratio": 1.5}
}
```

#### Scenario: Get strategy schema
- **WHEN** `GET /api/v1/strategy/schema/ma-cross` is called
- **THEN** it SHALL return the strategy metadata including default params

#### Scenario: Unknown strategy name
- **WHEN** `GET /api/v1/strategy/schema/nonexistent` is called
- **THEN** it SHALL return HTTP 404
