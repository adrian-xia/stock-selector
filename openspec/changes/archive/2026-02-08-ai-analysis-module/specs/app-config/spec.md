## ADDED Requirements

### Requirement: Gemini AI configuration
The settings SHALL include Gemini AI configuration parameters:
- `GEMINI_API_KEY` (str, default: `""`) — Gemini API key. Empty string means AI is disabled.
- `GEMINI_MODEL_ID` (str, default: `"gemini-2.0-flash"`) — Gemini model identifier
- `GEMINI_MAX_TOKENS` (int, default: `4000`) — maximum output tokens per request
- `GEMINI_TIMEOUT` (int, default: `30`) — request timeout in seconds
- `GEMINI_MAX_RETRIES` (int, default: `2`) — retry count on transient errors
- `AI_DAILY_BUDGET_USD` (float, default: `1.0`) — daily spending limit in USD (for logging/warning only in V1)

#### Scenario: Default Gemini configuration
- **WHEN** no Gemini environment variables are set
- **THEN** `settings.gemini_api_key` SHALL return `""`
- **AND** `settings.gemini_model_id` SHALL return `"gemini-2.0-flash"`

#### Scenario: Custom Gemini API key
- **WHEN** `GEMINI_API_KEY=AIzaSy...` is set in `.env`
- **THEN** `settings.gemini_api_key` SHALL return that value

#### Scenario: Custom model ID
- **WHEN** `GEMINI_MODEL_ID=gemini-2.5-flash` is set in `.env`
- **THEN** `settings.gemini_model_id` SHALL return `"gemini-2.5-flash"`

## MODIFIED Requirements

### Requirement: .env.example template
The project SHALL include a `.env.example` file documenting all available configuration variables with example values and comments.

The `.env.example` file SHALL include the following AI-related entries:
```
# --- AI (Gemini) ---
GEMINI_API_KEY=
GEMINI_MODEL_ID=gemini-2.0-flash
GEMINI_MAX_TOKENS=4000
GEMINI_TIMEOUT=30
GEMINI_MAX_RETRIES=2
AI_DAILY_BUDGET_USD=1.0
```

#### Scenario: Developer onboarding
- **WHEN** a developer clones the repository
- **THEN** they SHALL be able to copy `.env.example` to `.env` and fill in their local values to get the application running

#### Scenario: AI configuration in .env.example
- **WHEN** a developer reviews `.env.example`
- **THEN** they SHALL see all Gemini-related configuration variables with comments explaining their purpose
