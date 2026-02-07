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

#### Scenario: Developer onboarding
- **WHEN** a developer clones the repository
- **THEN** they SHALL be able to copy `.env.example` to `.env` and fill in their local values to get the application running
