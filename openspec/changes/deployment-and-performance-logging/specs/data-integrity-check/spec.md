## ADDED Requirements

### Requirement: Startup data integrity check
The system SHALL automatically check data integrity when the scheduler starts, detecting and filling missing data for recent trading days.

The check SHALL:
- Run automatically when the scheduler service starts
- Check the most recent N days (configurable, default 30 days)
- Identify missing trading days in the database
- Automatically backfill missing data for detected gaps
- Log the check results and any backfill operations

#### Scenario: No missing data on startup
- **WHEN** scheduler starts and all recent trading days have complete data
- **THEN** system SHALL log "Data integrity check passed: no missing data" and proceed normally

#### Scenario: Missing data detected on startup
- **WHEN** scheduler starts and data for 3 trading days is missing
- **THEN** system SHALL log "Data integrity check: missing 3 days" and automatically backfill those days

#### Scenario: Service stopped for multiple days
- **WHEN** service was stopped for 5 days and restarts
- **THEN** system SHALL detect missing data for those 5 days and backfill them before starting scheduled tasks

#### Scenario: Configurable check window
- **WHEN** `DATA_INTEGRITY_CHECK_DAYS=60` is configured
- **THEN** system SHALL check the most recent 60 days for missing data

#### Scenario: Skip check on non-trading days
- **WHEN** scheduler starts on a weekend or holiday
- **THEN** system SHALL skip the integrity check and log "Non-trading day, skipping integrity check"

### Requirement: Manual data backfill command
The system SHALL provide a CLI command to manually backfill missing data for a specified date range.

The command SHALL:
- Accept start and end dates as parameters
- Check which dates in the range are trading days
- Skip dates that already have complete data
- Sync data only for missing trading days
- Log progress and results

#### Scenario: Backfill specific date range
- **WHEN** user runs `uv run python -m app.data.cli backfill-daily --start 2026-01-01 --end 2026-01-31`
- **THEN** system SHALL backfill missing data for all trading days in January 2026

#### Scenario: Skip existing data
- **WHEN** backfill command runs and some dates already have data
- **THEN** system SHALL skip those dates and log "Skipping 2026-01-15: data already exists"

#### Scenario: Backfill only trading days
- **WHEN** backfill command runs for a date range including weekends
- **THEN** system SHALL only sync data for trading days and skip non-trading days

#### Scenario: Backfill with progress logging
- **WHEN** backfill command processes multiple days
- **THEN** system SHALL log progress after each day (e.g., "Backfilled 5/20 days")

### Requirement: Data initialization wizard
The system SHALL provide an interactive initialization wizard for first-time deployment.

The wizard SHALL:
- Detect if the database is empty or has minimal data
- Prompt user to select initialization scope (1 year, 3 years, custom range)
- Sync stock list before syncing daily data
- Sync daily data for the selected date range
- Sync adjustment factors for the selected date range
- Compute technical indicators after data sync
- Display progress and estimated time remaining

#### Scenario: First-time initialization with 1 year data
- **WHEN** user runs `uv run python scripts/init_data.py` and selects "1 year"
- **THEN** system SHALL sync stock list, daily data, adjustment factors, and technical indicators for the past 365 days

#### Scenario: Skip initialization if data exists
- **WHEN** initialization wizard runs and database already has substantial data (>100 days)
- **THEN** system SHALL prompt "Database already contains data. Continue anyway? (y/n)"

#### Scenario: Custom date range initialization
- **WHEN** user selects "Custom range" and enters start/end dates
- **THEN** system SHALL initialize data for the specified date range

#### Scenario: Initialization progress display
- **WHEN** initialization wizard is syncing data
- **THEN** system SHALL display progress for each step (e.g., "Syncing daily data: 50/365 days complete")

### Requirement: Detect missing data gaps
The system SHALL provide a function to detect gaps in daily data for all stocks.

#### Scenario: Detect gaps in date range
- **WHEN** `detect_missing_dates(start_date, end_date)` is called
- **THEN** system SHALL return a list of trading days that are missing data for any listed stock

#### Scenario: No gaps detected
- **WHEN** all trading days in the range have complete data
- **THEN** function SHALL return an empty list

#### Scenario: Partial gaps detected
- **WHEN** some stocks are missing data for certain days
- **THEN** function SHALL return those dates and log which stocks are affected

### Requirement: Avoid duplicate data sync
All data backfill operations SHALL check for existing data before syncing to avoid duplicates.

#### Scenario: Skip sync if data exists
- **WHEN** backfill attempts to sync data for a date that already exists in the database
- **THEN** system SHALL skip that date and NOT make API calls or database writes

#### Scenario: Sync only missing stocks
- **WHEN** a trading day has data for 90% of stocks but 10% are missing
- **THEN** system SHALL only sync data for the missing 10% of stocks
