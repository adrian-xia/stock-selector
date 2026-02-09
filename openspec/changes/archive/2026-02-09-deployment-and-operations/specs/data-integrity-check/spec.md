## ADDED Requirements

### Requirement: Detect missing trading dates
The system SHALL provide a method to detect missing trading dates in the database for a given date range.

The method SHALL:
- Query all trading dates from the trade calendar within the specified range
- Query existing data dates from the `stock_daily` table
- Calculate missing dates by comparing trading dates with existing data dates
- Return a list of missing trading dates

#### Scenario: No missing dates
- **WHEN** `detect_missing_dates(start_date, end_date)` is called and all trading dates have data
- **THEN** it SHALL return an empty list

#### Scenario: Some missing dates
- **WHEN** `detect_missing_dates(start_date, end_date)` is called and some trading dates are missing data
- **THEN** it SHALL return a list of missing trading dates in ascending order

#### Scenario: All dates missing
- **WHEN** `detect_missing_dates(start_date, end_date)` is called and no data exists
- **THEN** it SHALL return all trading dates in the range

### Requirement: Check data integrity on startup
The system SHALL check data integrity on application startup and automatically backfill missing data.

The check SHALL:
- Run automatically when the scheduler starts (unless `--skip-integrity-check` is specified)
- Check the most recent N days (configurable via `DATA_INTEGRITY_CHECK_DAYS`, default 30)
- Detect missing trading dates using `detect_missing_dates()`
- Automatically backfill missing dates using batch synchronization
- Log the check results and backfill progress

#### Scenario: Startup check with no missing data
- **WHEN** the scheduler starts and all recent data is complete
- **THEN** it SHALL log "数据完整性检查：最近 30 天数据完整" and proceed with normal operation

#### Scenario: Startup check with missing data
- **WHEN** the scheduler starts and some recent trading dates are missing
- **THEN** it SHALL log "数据完整性检查：发现 N 个缺失交易日" and automatically backfill the missing dates

#### Scenario: Skip integrity check
- **WHEN** the scheduler starts with `--skip-integrity-check` flag
- **THEN** it SHALL skip the data integrity check and proceed directly to normal operation

#### Scenario: Backfill failure
- **WHEN** automatic backfill fails for some dates
- **THEN** the system SHALL log the failure details but continue with normal operation

### Requirement: Manual backfill command
The system SHALL provide a CLI command to manually backfill missing daily data for a specified date range.

The command SHALL:
- Accept `--start` and `--end` date parameters
- Filter to only trading dates (skip non-trading dates)
- Check existing data and skip dates that already have data
- Use batch synchronization for efficient backfilling
- Support `--rate-limit` parameter to reduce sync speed (avoid API rate limiting)
- Log progress and results

#### Scenario: Backfill with date range
- **WHEN** user runs `python -m app.data.cli backfill-daily --start 2024-01-01 --end 2024-01-31`
- **THEN** the system SHALL backfill all missing trading dates in January 2024

#### Scenario: Skip existing data
- **WHEN** backfill command runs and some dates already have data
- **THEN** it SHALL skip those dates and only sync missing dates

#### Scenario: Skip non-trading dates
- **WHEN** backfill command runs for a date range including weekends
- **THEN** it SHALL only sync trading dates and skip non-trading dates

#### Scenario: Rate limiting
- **WHEN** user runs backfill with `--rate-limit 5`
- **THEN** the system SHALL limit concurrent requests to 5 (instead of default 10)

### Requirement: Configuration for integrity check
The system SHALL provide configuration options for data integrity checking.

Configuration options:
- `DATA_INTEGRITY_CHECK_DAYS`: Number of recent days to check (default: 30)
- `DATA_INTEGRITY_CHECK_ENABLED`: Enable/disable startup check (default: true)

#### Scenario: Custom check window
- **WHEN** `DATA_INTEGRITY_CHECK_DAYS=60` is configured
- **THEN** the startup check SHALL verify the most recent 60 days

#### Scenario: Disable startup check
- **WHEN** `DATA_INTEGRITY_CHECK_ENABLED=false` is configured
- **THEN** the startup check SHALL be skipped (equivalent to `--skip-integrity-check`)
