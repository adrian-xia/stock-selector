## ADDED Requirements

### Requirement: BaseStrategy abstract class
The system SHALL provide a `BaseStrategy` abstract base class that all strategies inherit from directly (flat inheritance, no intermediate abstract subclasses).

`BaseStrategy` SHALL define the following attributes:
- `name: str` — unique strategy identifier (kebab-case, e.g., `"ma-cross"`)
- `display_name: str` — human-readable name (e.g., `"均线金叉"`)
- `category: str` — one of `"technical"` or `"fundamental"`
- `description: str` — one-sentence description of the strategy logic
- `default_params: dict` — default parameter values

`BaseStrategy.__init__` SHALL accept an optional `params: dict` that overrides `default_params`.

#### Scenario: Strategy instantiation with default params
- **WHEN** a strategy is instantiated without params: `MACrossStrategy()`
- **THEN** `self.params` SHALL equal `self.default_params`

#### Scenario: Strategy instantiation with custom params
- **WHEN** a strategy is instantiated with `MACrossStrategy(params={"fast": 10})`
- **THEN** `self.params` SHALL be `default_params` merged with `{"fast": 10}` (custom overrides defaults)

### Requirement: filter_batch interface
Every strategy SHALL implement the `filter_batch` method with the following signature:

```python
async def filter_batch(
    self,
    df: pd.DataFrame,
    target_date: date,
) -> pd.Series
```

- `df`: A DataFrame where each row represents one stock on `target_date`. Columns include stock_daily fields (`ts_code`, `trade_date`, `open`, `high`, `low`, `close`, `vol`, `amount`, `turnover_rate`) and technical_daily fields (`ma5`, `ma10`, ..., `atr14`) and finance_indicator fields (`pe_ttm`, `pb`, `roe`, etc.).
- `target_date`: The screening date.
- Returns: A boolean `pd.Series` aligned with `df.index`. `True` means the stock passes this strategy's filter.

The method SHALL NOT modify the input DataFrame.

#### Scenario: Strategy returns boolean Series
- **WHEN** `filter_batch(df, date(2026, 2, 7))` is called with a 4000-row DataFrame
- **THEN** it SHALL return a `pd.Series` of length 4000 with dtype `bool`

#### Scenario: Strategy handles missing indicator columns gracefully
- **WHEN** `filter_batch` is called and a required indicator column contains NaN values
- **THEN** the strategy SHALL return `False` for rows with NaN in required columns (not raise an error)

#### Scenario: Strategy does not mutate input
- **WHEN** `filter_batch` is called
- **THEN** the original `df` SHALL remain unchanged after the call
