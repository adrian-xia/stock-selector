## ADDED Requirements

### Requirement: AIManager class
The system SHALL provide an `AIManager` class in `app/ai/manager.py` that orchestrates AI analysis for candidate stocks.

The constructor SHALL accept:
- `settings: Settings` — application settings containing Gemini configuration

AIManager SHALL lazily initialize the `GeminiClient` on first use. If neither `GEMINI_API_KEY` is set nor `GEMINI_USE_ADC` is enabled, it SHALL log a warning and operate in disabled mode (all calls return original picks unchanged).

The `_get_client()` method SHALL pass `use_adc=settings.gemini_use_adc` to the `GeminiClient` constructor.

#### Scenario: Initialization with valid API key
- **WHEN** `AIManager(settings)` is constructed and `settings.gemini_api_key` is non-empty
- **THEN** it SHALL be in enabled mode and ready to perform analysis on first call

#### Scenario: Initialization with ADC enabled
- **WHEN** `AIManager(settings)` is constructed and `settings.gemini_use_adc` is `True` (with empty API key)
- **THEN** it SHALL be in enabled mode and ready to perform analysis on first call

#### Scenario: Initialization without API key and without ADC
- **WHEN** `AIManager(settings)` is constructed and both `settings.gemini_api_key` is empty and `settings.gemini_use_adc` is `False`
- **THEN** it SHALL log a warning "AI 分析未启用：GEMINI_API_KEY 未配置且 ADC 未启用"
- **AND** `is_enabled` property SHALL return `False`

### Requirement: analyze method
The `AIManager` SHALL provide an async `analyze()` method:

```python
async def analyze(
    self,
    picks: list[StockPick],
    market_data: dict[str, dict],
    target_date: date,
) -> list[StockPick]
```

It SHALL:
1. Return `picks` unchanged if AI is disabled or `picks` is empty
2. Build the analysis prompt via `build_analysis_prompt()`
3. Call `GeminiClient.chat_json()` to get AI analysis
4. Validate the response with `AIAnalysisResponse`
5. Merge AI scores into `StockPick` objects (set `ai_score` and `ai_summary`)
6. Re-sort picks by `ai_score` descending (stocks without AI score go to the end)
7. Return the updated picks list

#### Scenario: Successful analysis of 10 stocks
- **WHEN** `analyze(picks, market_data, target_date)` is called with 10 picks and AI is enabled
- **THEN** it SHALL return 10 picks with `ai_score` and `ai_summary` populated
- **AND** picks SHALL be sorted by `ai_score` descending

#### Scenario: AI disabled
- **WHEN** `analyze(picks, market_data, target_date)` is called and AI is disabled
- **THEN** it SHALL return the original `picks` list unchanged with `ai_score=None`

#### Scenario: Empty picks list
- **WHEN** `analyze([], market_data, target_date)` is called
- **THEN** it SHALL return an empty list without calling the Gemini API

### Requirement: Graceful failure handling
When the Gemini API call fails (timeout, API error, response parse error), the `analyze()` method SHALL:
1. Log a warning with the error details
2. Return the original `picks` list unchanged (all `ai_score` remain `None`)
3. NOT raise any exception

#### Scenario: Gemini timeout
- **WHEN** the Gemini API times out during `analyze()`
- **THEN** it SHALL log `"AI 分析超时，跳过 AI 评分"` at WARNING level
- **AND** return the original picks with `ai_score=None`

#### Scenario: Invalid JSON response from Gemini
- **WHEN** the Gemini API returns invalid JSON or mismatched schema
- **THEN** it SHALL log `"AI 响应解析失败，跳过 AI 评分"` at WARNING level
- **AND** return the original picks with `ai_score=None`

### Requirement: Partial response handling
When the AI response contains fewer stocks than the input, the `analyze()` method SHALL:
1. Apply AI scores to matched stocks
2. Leave unmatched stocks with `ai_score=None`
3. Log a warning indicating the mismatch count

#### Scenario: AI returns 8 results for 10 input stocks
- **WHEN** the AI response contains analysis for only 8 of 10 input stocks
- **THEN** the 8 matched stocks SHALL have `ai_score` populated
- **AND** the 2 unmatched stocks SHALL have `ai_score=None`
- **AND** a warning SHALL be logged

### Requirement: get_ai_manager singleton function
The system SHALL provide a module-level `get_ai_manager()` function that returns a lazily-initialized singleton `AIManager` instance:

```python
def get_ai_manager() -> AIManager
```

#### Scenario: Singleton behavior
- **WHEN** `get_ai_manager()` is called multiple times
- **THEN** it SHALL return the same `AIManager` instance each time

### Requirement: AIManager 结果写入与成本控制
AIManager SHALL 增加结果持久化写入方法和每日调用上限控制。

#### Scenario: 写入分析结果到数据库
- **WHEN** AI 分析完成后调用 `save_results(picks, trade_date)`
- **THEN** 将分析结果 UPSERT 到 ai_analysis_results 表

#### Scenario: 每日调用上限
- **WHEN** 当日 AI 调用次数已达到 `AI_DAILY_CALL_LIMIT`（默认 5）
- **THEN** 跳过 AI 分析，记录日志，返回原始 picks

#### Scenario: Token 用量记录
- **WHEN** AI 分析完成
- **THEN** 将 prompt_tokens、completion_tokens、total_tokens 记录到 ai_analysis_results.token_usage

#### Scenario: 查询当日结果
- **WHEN** 调用 `get_results(trade_date)`
- **THEN** 返回当日所有 AI 分析结果列表
