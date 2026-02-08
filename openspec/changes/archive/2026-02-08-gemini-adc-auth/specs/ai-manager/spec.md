## MODIFIED Requirements

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
