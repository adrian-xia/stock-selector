## ADDED Requirements

### Requirement: Startup data integrity check
The scheduler SHALL check data integrity on startup and automatically backfill missing data before starting scheduled jobs.

The check SHALL:
- Run automatically when the scheduler starts (unless `--skip-integrity-check` is specified)
- Check the most recent N days (configurable via `DATA_INTEGRITY_CHECK_DAYS`, default 30)
- Detect missing trading dates by comparing trade calendar with existing data
- Automatically backfill missing dates using batch synchronization
- Log the check results and backfill progress
- Continue with normal scheduler operation after check completes

#### Scenario: Startup with complete data
- **WHEN** the scheduler starts and all recent data is complete
- **THEN** it SHALL log "数据完整性检查：最近 30 天数据完整" and start scheduled jobs

#### Scenario: Startup with missing data
- **WHEN** the scheduler starts and some recent trading dates are missing
- **THEN** it SHALL log "数据完整性检查：发现 N 个缺失交易日，开始自动补齐" and backfill before starting jobs

#### Scenario: Skip integrity check via flag
- **WHEN** the scheduler starts with `--skip-integrity-check` flag
- **THEN** it SHALL skip the data integrity check and start scheduled jobs immediately

#### Scenario: Skip integrity check via config
- **WHEN** `DATA_INTEGRITY_CHECK_ENABLED=false` is configured
- **THEN** the scheduler SHALL skip the data integrity check on startup

#### Scenario: Backfill failure on startup
- **WHEN** automatic backfill fails for some dates during startup check
- **THEN** the scheduler SHALL log the failure details but continue starting scheduled jobs

### Requirement: Startup command-line arguments
The scheduler SHALL support command-line arguments to control startup behavior.

Supported arguments:
- `--skip-integrity-check`: Skip data integrity check on startup
- `--foreground`: Run in foreground mode (log to stdout instead of file)

#### Scenario: Foreground mode
- **WHEN** the scheduler starts with `--foreground` flag
- **THEN** it SHALL log all output to stdout instead of log files

#### Scenario: Combined flags
- **WHEN** the scheduler starts with `--skip-integrity-check --foreground`
- **THEN** it SHALL skip integrity check and run in foreground mode
