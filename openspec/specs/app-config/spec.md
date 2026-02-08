## ADDED Requirements

### Requirement: Pydantic Settings configuration
The system SHALL use `pydantic-settings` (`BaseSettings`) to load all application configuration from environment variables and a `.env` file. The `.env` file SHALL be located at the project root.

#### Scenario: Load configuration from .env file
- **WHEN** the application starts
- **THEN** it SHALL read configuration values from the `.env` file at the project root
- **AND** environment variables SHALL take precedence over `.env` file values

#### Scenario: Missing required configuration
- **WHEN** a required configuration value (e.g., `DATABASE_URL`) is not set in either environment variables or `.env`
- **THEN** the application SHALL fail to start with a clear validation error message

### Requirement: Database configuration
The settings SHALL include database connection parameters:
- `DATABASE_URL` (str, required): PostgreSQL async connection string
- `DB_POOL_SIZE` (int, default: 5): connection pool size
- `DB_MAX_OVERFLOW` (int, default: 10): max overflow connections
- `DB_ECHO` (bool, default: False): enable SQL logging

#### Scenario: Database URL configuration
- **WHEN** `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/stock_selector` is set in `.env`
- **THEN** `settings.database_url` SHALL return that value

### Requirement: Redis configuration
The settings SHALL include Redis connection parameters:
- `REDIS_HOST` (str, default: `"localhost"`)
- `REDIS_PORT` (int, default: 6379)
- `REDIS_DB` (int, default: 0)
- `REDIS_PASSWORD` (str, default: `""`)

#### Scenario: Default Redis configuration
- **WHEN** no Redis environment variables are set
- **THEN** the settings SHALL use default values (localhost:6379, db=0, no password)

### Requirement: Data source configuration
The settings SHALL include configuration for each data source:

BaoStock:
- `BAOSTOCK_RETRY_COUNT` (int, default: 3)
- `BAOSTOCK_RETRY_INTERVAL` (float, default: 2.0)
- `BAOSTOCK_TIMEOUT` (int, default: 30)
- `BAOSTOCK_QPS_LIMIT` (int, default: 5)

AKShare:
- `AKSHARE_RETRY_COUNT` (int, default: 3)
- `AKSHARE_RETRY_INTERVAL` (float, default: 1.0)
- `AKSHARE_TIMEOUT` (int, default: 20)
- `AKSHARE_QPS_LIMIT` (int, default: 10)

#### Scenario: Custom BaoStock retry count
- **WHEN** `BAOSTOCK_RETRY_COUNT=5` is set in `.env`
- **THEN** `settings.baostock_retry_count` SHALL return `5`

### Requirement: ETL configuration
The settings SHALL include ETL processing parameters:
- `ETL_BATCH_SIZE` (int, default: 5000)
- `ETL_COMMIT_INTERVAL` (int, default: 10)

#### Scenario: Default ETL batch size
- **WHEN** no ETL environment variables are set
- **THEN** `settings.etl_batch_size` SHALL return `5000`

### Requirement: Application configuration
The settings SHALL include general application parameters:
- `APP_NAME` (str, default: `"stock-selector"`)
- `APP_ENV` (str, default: `"development"`)
- `LOG_LEVEL` (str, default: `"INFO"`)
- `API_PREFIX` (str, default: `"/api/v1"`)

#### Scenario: Production environment
- **WHEN** `APP_ENV=production` is set
- **THEN** `settings.app_env` SHALL return `"production"`

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

#### Scenario: Cache configuration in .env.example
- **WHEN** a developer reviews `.env.example`
- **THEN** they SHALL see all cache-related configuration variables with comments explaining their purpose

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

### Requirement: Gemini ADC configuration
The settings SHALL include an ADC toggle for Gemini authentication:
- `GEMINI_USE_ADC` (bool, default: `false`) — 是否使用 Google Application Default Credentials 认证

#### Scenario: Default ADC configuration
- **WHEN** no `GEMINI_USE_ADC` environment variable is set
- **THEN** `settings.gemini_use_adc` SHALL return `False`

#### Scenario: Enable ADC
- **WHEN** `GEMINI_USE_ADC=true` is set in `.env`
- **THEN** `settings.gemini_use_adc` SHALL return `True`

### Requirement: Cache configuration
The settings SHALL include Redis cache behavior parameters:
- `CACHE_TECH_TTL` (int, default: `90000`) — 技术指标缓存 TTL，单位秒（默认 25 小时）
- `CACHE_PIPELINE_RESULT_TTL` (int, default: `172800`) — 选股结果缓存 TTL，单位秒（默认 48 小时）
- `CACHE_WARMUP_ON_STARTUP` (bool, default: `True`) — 应用启动时是否执行缓存预热
- `CACHE_REFRESH_BATCH_SIZE` (int, default: `500`) — 全量刷新时 Redis Pipeline 批次大小

#### Scenario: Default cache configuration
- **WHEN** no cache environment variables are set
- **THEN** `settings.cache_tech_ttl` SHALL return `90000`
- **AND** `settings.cache_pipeline_result_ttl` SHALL return `172800`
- **AND** `settings.cache_warmup_on_startup` SHALL return `True`
- **AND** `settings.cache_refresh_batch_size` SHALL return `500`

#### Scenario: Custom cache TTL
- **WHEN** `CACHE_TECH_TTL=3600` is set in `.env`
- **THEN** `settings.cache_tech_ttl` SHALL return `3600`
