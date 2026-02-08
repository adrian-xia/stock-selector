## ADDED Requirements

### Requirement: Stock analysis prompt template
The system SHALL provide a `build_analysis_prompt()` function in `app/ai/prompts.py` that constructs a comprehensive analysis prompt for a batch of candidate stocks.

```python
def build_analysis_prompt(
    picks: list[StockPick],
    market_data: dict[str, dict],
    target_date: date,
) -> str
```

Parameters:
- `picks` — candidate stocks from Layer 4
- `market_data` — dict keyed by `ts_code`, containing `close`, `pct_chg`, `ma5`, `ma10`, `ma20`, `rsi6`, `macd_dif`, `macd_dea`, `vol_ratio`, and fundamental fields (`pe_ttm`, `pb`, `roe`, `profit_yoy`) when available
- `target_date` — the analysis date

The prompt SHALL:
- Assign the model the role of a senior A-share investment analyst
- Include each stock's technical indicators, fundamental data, and matched strategy names
- Request a JSON response with an `analysis` array containing per-stock objects
- Specify the exact output JSON schema in the prompt

#### Scenario: Build prompt for 5 stocks
- **WHEN** `build_analysis_prompt(picks, market_data, date(2026, 2, 7))` is called with 5 stock picks
- **THEN** it SHALL return a string containing all 5 stocks' data and the expected JSON output format

#### Scenario: Missing market data for a stock
- **WHEN** `market_data` does not contain an entry for a stock in `picks`
- **THEN** the prompt SHALL include that stock with "数据缺失" notation and still request analysis

### Requirement: Expected AI response schema
The prompt SHALL request the model to return JSON in the following format:

```json
{
  "analysis": [
    {
      "ts_code": "600519.SH",
      "score": 85,
      "signal": "BUY",
      "reasoning": "..."
    }
  ]
}
```

Where:
- `ts_code` (str) — stock code matching the input
- `score` (int) — AI confidence score from 0 to 100
- `signal` (str) — one of `"STRONG_BUY"`, `"BUY"`, `"HOLD"`, `"SELL"`, `"STRONG_SELL"`
- `reasoning` (str) — brief Chinese explanation of the analysis rationale

#### Scenario: Response schema validation
- **WHEN** the model returns a valid response
- **THEN** each item in the `analysis` array SHALL contain all four fields (`ts_code`, `score`, `signal`, `reasoning`)

### Requirement: AIAnalysisItem Pydantic model
The system SHALL provide an `AIAnalysisItem` Pydantic model in `app/ai/schemas.py` for validating individual stock analysis results:

```python
class AIAnalysisItem(BaseModel):
    ts_code: str
    score: int = Field(ge=0, le=100)
    signal: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    reasoning: str
```

#### Scenario: Valid analysis item
- **WHEN** `AIAnalysisItem(ts_code="600519.SH", score=85, signal="BUY", reasoning="均线多头")` is constructed
- **THEN** it SHALL succeed without validation errors

#### Scenario: Score out of range
- **WHEN** `AIAnalysisItem(ts_code="600519.SH", score=150, signal="BUY", reasoning="test")` is constructed
- **THEN** it SHALL raise a `ValidationError`

### Requirement: AIAnalysisResponse Pydantic model
The system SHALL provide an `AIAnalysisResponse` model for validating the complete AI response:

```python
class AIAnalysisResponse(BaseModel):
    analysis: list[AIAnalysisItem]
```

#### Scenario: Parse valid response
- **WHEN** `AIAnalysisResponse.model_validate({"analysis": [...]})` is called with valid data
- **THEN** it SHALL return a validated response object

#### Scenario: Missing analysis field
- **WHEN** `AIAnalysisResponse.model_validate({"results": [...]})` is called with wrong field name
- **THEN** it SHALL raise a `ValidationError`
