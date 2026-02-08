## ADDED Requirements

### Requirement: Pipeline execute function
The system SHALL provide an `execute_pipeline()` async function that runs the full 5-layer screening funnel and returns the final stock picks.

Signature:
```python
async def execute_pipeline(
    session_factory: async_sessionmaker,
    strategy_names: list[str],
    target_date: date,
    base_filter: dict | None = None,
    top_n: int = 30,
) -> PipelineResult
```

`PipelineResult` SHALL be a dataclass containing:
- `target_date: date`
- `picks: list[StockPick]` — final stock picks sorted by match count descending
- `layer_stats: dict` — count of stocks passing each layer
- `elapsed_ms: int` — total execution time in milliseconds
- `ai_enabled: bool` — whether AI analysis was attempted

`StockPick` SHALL be a dataclass containing:
- `ts_code: str`
- `name: str`
- `close: float`
- `pct_chg: float`
- `matched_strategies: list[str]` — names of strategies that selected this stock
- `match_count: int`
- `ai_score: int | None` — AI confidence score 0-100, default `None`
- `ai_signal: str | None` — AI signal string, default `None`
- `ai_summary: str | None` — AI analysis reasoning, default `None`

#### Scenario: Full pipeline execution
- **WHEN** `execute_pipeline(session_factory, ["ma-cross", "low-pe-high-roe"], date(2026, 2, 7))` is called
- **THEN** it SHALL return a `PipelineResult` with picks sorted by `match_count` descending
- **AND** `layer_stats` SHALL contain keys `"layer1"`, `"layer2"`, `"layer3"`, `"layer4"`

#### Scenario: No strategies selected
- **WHEN** `execute_pipeline(session_factory, [], date(2026, 2, 7))` is called
- **THEN** it SHALL return a `PipelineResult` with empty `picks`

### Requirement: Layer 1 SQL base filter
Layer 1 SHALL query the database to get all tradeable stocks on `target_date`, filtering out:
- Stocks with `list_status != 'L'` (not listed)
- Stocks with `vol = 0` on `target_date` (suspended)
- Stocks where the stock name contains `"ST"` (ST stocks)

The `base_filter` dict MAY override defaults:
- `exclude_st: bool` (default `True`)
- `min_turnover_rate: float` (default `0.001`)

#### Scenario: Layer 1 filters out ST and suspended stocks
- **WHEN** Layer 1 runs on a date with 5300 total stocks
- **THEN** it SHALL return approximately 4000 stocks (excluding ST, suspended, delisted)

#### Scenario: Layer 1 with custom turnover filter
- **WHEN** `base_filter={"min_turnover_rate": 0.01}` is provided
- **THEN** Layer 1 SHALL additionally exclude stocks with `turnover_rate < 0.01`

### Requirement: Layer 2 technical strategy screening
Layer 2 SHALL load a market snapshot DataFrame by joining `stock_daily` and `technical_daily` for the stocks passing Layer 1 on `target_date`.

It SHALL run all selected strategies with `category == "technical"` via `filter_batch()`.

Stocks that pass ANY technical strategy (OR logic across technical strategies) SHALL advance to Layer 3.

#### Scenario: Technical screening with multiple strategies
- **WHEN** Layer 2 runs with strategies `["ma-cross", "rsi-oversold"]` on 4000 stocks
- **THEN** a stock that passes either `ma-cross` OR `rsi-oversold` SHALL be included in the output

#### Scenario: No technical strategies selected
- **WHEN** no technical strategies are in the selected list
- **THEN** Layer 2 SHALL pass all Layer 1 stocks through to Layer 3

### Requirement: Layer 3 fundamental strategy screening
Layer 3 SHALL enrich the DataFrame with `finance_indicator` data (latest report per stock where `ann_date <= target_date`).

It SHALL run all selected strategies with `category == "fundamental"` via `filter_batch()`.

Stocks that pass ANY fundamental strategy SHALL advance to Layer 4.

#### Scenario: Fundamental screening
- **WHEN** Layer 3 runs with strategy `["low-pe-high-roe"]` on 500 stocks
- **THEN** only stocks meeting PE < 30 AND ROE > 15% AND profit_yoy > 20% SHALL pass

#### Scenario: No fundamental strategies selected
- **WHEN** no fundamental strategies are in the selected list
- **THEN** Layer 3 SHALL pass all Layer 2 stocks through to Layer 4

### Requirement: Layer 4 ranking and top-N selection
Layer 4 SHALL rank stocks by the number of strategies they matched (across all layers), then select the top `top_n` stocks.

#### Scenario: Ranking by match count
- **WHEN** Stock A matched 3 strategies and Stock B matched 1 strategy
- **THEN** Stock A SHALL rank higher than Stock B

#### Scenario: Top-N cutoff
- **WHEN** 100 stocks pass Layers 1-3 and `top_n=30`
- **THEN** Layer 4 SHALL return only the top 30 stocks by match count

### Requirement: Layer 5 AI placeholder
Layer 5 SHALL call `AIManager.analyze()` to perform AI analysis on the candidate stocks from Layer 4. It SHALL:

1. Obtain the `AIManager` singleton via `get_ai_manager()`
2. Build `market_data` dict from the pipeline's market snapshot DataFrame for the stocks in `picks`
3. Call `await ai_manager.analyze(picks, market_data, target_date)`
4. Return the AI-scored and re-sorted picks

If AIManager is disabled (no API key configured), Layer 5 SHALL behave as a pass-through and return Layer 4 results unchanged.

The function signature SHALL be:
```python
async def _layer5_ai_analysis(
    picks: list[StockPick],
    market_snapshot: pd.DataFrame,
    target_date: date,
) -> list[StockPick]
```

#### Scenario: AI analysis enabled
- **WHEN** Layer 5 runs with AI enabled and 30 stock picks from Layer 4
- **THEN** it SHALL return picks re-sorted by `ai_score` descending
- **AND** each pick SHALL have `ai_score`, `ai_signal`, and `ai_summary` populated

#### Scenario: AI analysis disabled (no API key)
- **WHEN** Layer 5 runs with AI disabled (no `GEMINI_API_KEY`)
- **THEN** it SHALL return the same 30 picks from Layer 4 without modification

#### Scenario: AI analysis failure
- **WHEN** Layer 5 runs and the Gemini API call fails
- **THEN** it SHALL return the original Layer 4 picks with `ai_score=None`
- **AND** it SHALL log a warning

### Requirement: Previous day data for crossover detection
The Pipeline SHALL provide previous trading day indicator values for crossover-based strategies. When building the market snapshot DataFrame, it SHALL join the prior trading day's `technical_daily` row and add columns with `_prev` suffix (e.g., `ma5_prev`, `macd_dif_prev`, `kdj_k_prev`).

#### Scenario: Previous day columns available
- **WHEN** the market snapshot DataFrame is built for `target_date`
- **THEN** it SHALL contain `ma5_prev`, `ma10_prev`, `macd_dif_prev`, `macd_dea_prev`, `rsi6_prev`, `kdj_k_prev`, `kdj_d_prev`, `boll_lower_prev`, `close_prev` columns from the prior trading day
