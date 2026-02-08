## MODIFIED Requirements

### Requirement: Pydantic Settings configuration
The system SHALL use `pydantic-settings` (`BaseSettings`) to load all application configuration from environment variables and a `.env` file. The `.env` file SHALL be located at the project root.

#### Scenario: Load configuration from .env file
- **WHEN** the application starts
- **THEN** it SHALL read configuration values from the `.env` file at the project root
- **AND** environment variables SHALL take precedence over `.env` file values

#### Scenario: Missing required configuration
- **WHEN** a required configuration value (e.g., `DATABASE_URL`) is not set in either environment variables or `.env`
- **THEN** the application SHALL fail to start with a clear validation error message

## ADDED Requirements

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

### Requirement: .env.example template
The project SHALL include a `.env.example` file documenting all available configuration variables with example values and comments.

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

#### Scenario: Cache configuration in .env.example
- **WHEN** a developer reviews `.env.example`
- **THEN** they SHALL see all cache-related configuration variables with comments explaining their purpose
