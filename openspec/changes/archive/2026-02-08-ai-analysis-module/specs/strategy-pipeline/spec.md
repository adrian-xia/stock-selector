## MODIFIED Requirements

### Requirement: Layer 5 AI placeholder
Layer 5 SHALL call `AIManager.analyze()` to perform AI analysis on the candidate stocks from Layer 4. It SHALL:

1. Obtain the `AIManager` singleton via `get_ai_manager()`
2. Build `market_data` dict from the pipeline's market snapshot DataFrame for the stocks in `picks`
3. Call `await ai_manager.analyze(picks, market_data, target_date)`
4. Return the AI-scored and re-sorted picks

If AIManager is disabled (no API key configured), Layer 5 SHALL behave as a pass-through and return Layer 4 results unchanged.

The function signature SHALL change from:
```python
async def _layer5_ai_placeholder(picks: list[StockPick]) -> list[StockPick]
```
to:
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

### Requirement: Pipeline execute function
The `execute_pipeline()` function SHALL pass the `market_snapshot` DataFrame and `target_date` to Layer 5, and include `ai_enabled` status in the `PipelineResult`.

`PipelineResult` SHALL be extended with:
- `ai_enabled: bool` — whether AI analysis was attempted

`StockPick` SHALL be extended with:
- `ai_score: int | None` — AI confidence score 0-100, default `None`
- `ai_signal: str | None` — AI signal string, default `None`
- `ai_summary: str | None` — AI analysis reasoning, default `None`

#### Scenario: Full pipeline execution with AI
- **WHEN** `execute_pipeline()` is called with AI enabled
- **THEN** `PipelineResult.ai_enabled` SHALL be `True`
- **AND** `PipelineResult.picks` SHALL contain AI-scored stocks

#### Scenario: Full pipeline execution without AI
- **WHEN** `execute_pipeline()` is called without AI configured
- **THEN** `PipelineResult.ai_enabled` SHALL be `False`
- **AND** `PipelineResult.picks` SHALL have `ai_score=None` for all picks
