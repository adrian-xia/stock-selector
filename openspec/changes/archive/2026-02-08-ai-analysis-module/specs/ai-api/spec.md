## ADDED Requirements

### Requirement: AI fields in strategy run response
The `POST /api/v1/strategy/run` response SHALL include AI analysis fields in each stock pick when AI analysis has been performed.

The pick object in the response SHALL include:
- `ai_score` (int | null) — AI confidence score 0-100, null if AI was not executed
- `ai_signal` (str | null) — one of `"STRONG_BUY"`, `"BUY"`, `"HOLD"`, `"SELL"`, `"STRONG_SELL"`, null if AI was not executed
- `ai_summary` (str | null) — brief AI analysis reasoning in Chinese, null if AI was not executed

#### Scenario: Response with AI analysis
- **WHEN** `POST /api/v1/strategy/run` completes with AI enabled
- **THEN** each pick in the response SHALL include `ai_score`, `ai_signal`, and `ai_summary` fields with non-null values

#### Scenario: Response without AI analysis
- **WHEN** `POST /api/v1/strategy/run` completes with AI disabled or AI call failed
- **THEN** each pick in the response SHALL include `ai_score: null`, `ai_signal: null`, and `ai_summary: null`

### Requirement: AI status in pipeline response metadata
The strategy run response SHALL include an `ai_enabled` boolean field at the top level indicating whether AI analysis was attempted.

#### Scenario: AI enabled in response
- **WHEN** the pipeline runs with AI enabled and `GEMINI_API_KEY` configured
- **THEN** the response SHALL include `"ai_enabled": true`

#### Scenario: AI disabled in response
- **WHEN** the pipeline runs without `GEMINI_API_KEY` configured
- **THEN** the response SHALL include `"ai_enabled": false`
