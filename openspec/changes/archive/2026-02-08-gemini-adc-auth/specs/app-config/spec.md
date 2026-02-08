## ADDED Requirements

### Requirement: Gemini ADC configuration
The settings SHALL include an ADC toggle for Gemini authentication:
- `GEMINI_USE_ADC` (bool, default: `false`) — 是否使用 Google Application Default Credentials 认证

#### Scenario: Default ADC configuration
- **WHEN** no `GEMINI_USE_ADC` environment variable is set
- **THEN** `settings.gemini_use_adc` SHALL return `False`

#### Scenario: Enable ADC
- **WHEN** `GEMINI_USE_ADC=true` is set in `.env`
- **THEN** `settings.gemini_use_adc` SHALL return `True`

## MODIFIED Requirements

### Requirement: .env.example template
The project SHALL include a `.env.example` file documenting all available configuration variables with example values and comments.

The `.env.example` file SHALL include the following AI-related entries:
```
# --- AI (Gemini) ---
GEMINI_API_KEY=
GEMINI_USE_ADC=false                # 使用 Google ADC 认证（与 API Key 二选一）
GEMINI_MODEL_ID=gemini-2.0-flash
GEMINI_MAX_TOKENS=4000
GEMINI_TIMEOUT=30
GEMINI_MAX_RETRIES=2
AI_DAILY_BUDGET_USD=1.0
```

The `.env.example` file SHALL include the following cache-related entries:
```
# --- Cache (Redis) ---
CACHE_TECH_TTL=90000
CACHE_PIPELINE_RESULT_TTL=172800
CACHE_WARMUP_ON_STARTUP=true
CACHE_REFRESH_BATCH_SIZE=500
```

#### Scenario: Developer onboarding
- **WHEN** a developer clones the repository
- **THEN** they SHALL be able to copy `.env.example` to `.env` and fill in their local values to get the application running

#### Scenario: AI configuration in .env.example
- **WHEN** a developer reviews `.env.example`
- **THEN** they SHALL see all Gemini-related configuration variables including `GEMINI_USE_ADC` with comments explaining its purpose
