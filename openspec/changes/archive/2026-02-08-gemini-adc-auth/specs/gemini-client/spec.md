## MODIFIED Requirements

### Requirement: GeminiClient class
The system SHALL provide a `GeminiClient` class in `app/ai/clients/gemini.py` that wraps the `google-genai` SDK for async communication with Gemini Flash.

The constructor SHALL accept:
- `api_key: str | None = None` — Gemini API key（可选）
- `model_id: str` — model identifier (default `"gemini-2.0-flash"`)
- `timeout: int` — request timeout in seconds (default `30`)
- `max_retries: int` — retry count on transient errors (default `2`)
- `use_adc: bool = False` — 是否使用 Application Default Credentials 认证

认证优先级：
1. 若 `api_key` 非空，使用 API Key 方式：`genai.Client(api_key=api_key)`
2. 若 `use_adc=True` 且 `api_key` 为空，使用 ADC 方式：调用 `google.auth.default()` 获取 credentials，传给 `genai.Client(credentials=credentials)`
3. 两者都未提供时，SHALL 抛出 `ValueError`

#### Scenario: Successful initialization with API key
- **WHEN** `GeminiClient(api_key="valid-key")` is constructed
- **THEN** it SHALL create an internal `google.genai.Client` instance with the provided API key

#### Scenario: Successful initialization with ADC
- **WHEN** `GeminiClient(use_adc=True)` is constructed and ADC credentials are available
- **THEN** it SHALL call `google.auth.default()` to obtain credentials
- **AND** create an internal `google.genai.Client` instance with those credentials

#### Scenario: API key takes precedence over ADC
- **WHEN** `GeminiClient(api_key="valid-key", use_adc=True)` is constructed
- **THEN** it SHALL use the API key and ignore the ADC setting

#### Scenario: Neither API key nor ADC provided
- **WHEN** `GeminiClient()` is constructed without `api_key` and `use_adc=False`
- **THEN** it SHALL raise `ValueError` with message indicating either API key or ADC must be configured

#### Scenario: ADC credentials unavailable
- **WHEN** `GeminiClient(use_adc=True)` is constructed but ADC credentials are not configured in the environment
- **THEN** it SHALL raise `ValueError` with a message indicating ADC credentials could not be obtained
