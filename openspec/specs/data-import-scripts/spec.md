## ADDED Requirements

### Requirement: Full import script for daily bars
The system SHALL provide a CLI script for performing a full historical import of daily bar data. The script SHALL iterate over all listed stocks and fetch their complete daily history from the primary data source.

V1 simplification: No `import_progress` table or checkpoint/resume. If the import fails partway through, it can be re-run and will skip existing records via `ON CONFLICT DO NOTHING`.

#### Scenario: First-time full import
- **WHEN** the full import script is run against an empty `stock_daily` table
- **THEN** it SHALL fetch daily bars for all listed stocks from their listing date to today
- **AND** insert all records into `stock_daily` in batches
- **AND** log progress every 100 stocks

#### Scenario: Re-run after partial failure
- **WHEN** the full import script is re-run after a previous partial failure
- **THEN** it SHALL attempt to fetch data for all stocks again
- **AND** records that already exist (same ts_code + trade_date) SHALL be skipped via `ON CONFLICT DO NOTHING`
- **AND** only genuinely new records SHALL be inserted

#### Scenario: Import with index optimization
- **WHEN** the full import script is run with `--optimize-indexes` flag
- **THEN** it SHALL drop non-primary-key indexes on `stock_daily` before importing
- **AND** recreate the indexes after import completes
- **AND** run `ANALYZE stock_daily` to update statistics

### Requirement: Full import script for stock list
The system SHALL provide a CLI script (or a subcommand) for importing the complete A-share stock list into the `stocks` table.

#### Scenario: Import stock list
- **WHEN** the stock list import is run
- **THEN** it SHALL fetch all A-share stocks from the data source
- **AND** insert new stocks and update existing stocks' `list_status` and other fields

### Requirement: Full import script for trade calendar
The system SHALL provide a CLI script (or a subcommand) for importing the trade calendar into the `trade_calendar` table.

#### Scenario: Import trade calendar
- **WHEN** the trade calendar import is run for year 2025
- **THEN** it SHALL fetch all calendar dates for 2025 from the data source
- **AND** insert them into `trade_calendar` with correct `is_open` flags

### Requirement: Incremental daily sync
The system SHALL provide an incremental sync function that fetches only the latest trading day's data and inserts it into the database. This function is designed to be called by the scheduler after market close.

After syncing daily bar data, the system SHALL also fetch and update the adjustment factor for each stock on the synced date.

#### Scenario: Incremental sync on a trading day
- **WHEN** incremental sync is triggered on a trading day after market close
- **THEN** it SHALL check if today is a trading day via `trade_calendar`
- **AND** fetch today's daily bars for all listed stocks
- **AND** insert the data into `stock_daily`
- **AND** fetch and update the adj factor for each stock for today's date
- **AND** log a summary: `{"inserted": N, "skipped": M, "failed": F, "adj_factor_updated": A}`

#### Scenario: Incremental sync on a non-trading day
- **WHEN** incremental sync is triggered on a weekend or holiday
- **THEN** it SHALL detect that today is not a trading day
- **AND** skip the sync with a log message

### Requirement: CLI entry point
The system SHALL provide a unified CLI entry point for data management operations using Python's `argparse` or `click`.

Supported commands:
- `python -m app.data.cli import-all` — full import of all data types
- `python -m app.data.cli import-daily` — full import of daily bars only
- `python -m app.data.cli import-stocks` — import stock list
- `python -m app.data.cli import-calendar` — import trade calendar
- `python -m app.data.cli sync-daily` — incremental daily sync
- `python -m app.data.cli sync-adj-factor` — full import of adjustment factors
- `python -m app.data.cli compute-indicators` — full compute of technical indicators
- `python -m app.data.cli update-indicators` — incremental compute of technical indicators

#### Scenario: Run full import via CLI
- **WHEN** `python -m app.data.cli import-all` is executed
- **THEN** it SHALL run stock list import, then trade calendar import, then daily bars import in sequence
- **AND** log the total records imported for each data type

#### Scenario: Unknown command
- **WHEN** an unknown command is passed to the CLI
- **THEN** it SHALL print a help message listing available commands and exit with code 1

### Requirement: Import error handling
Import scripts SHALL handle individual stock failures gracefully without aborting the entire import.

#### Scenario: Single stock fetch failure during full import
- **WHEN** fetching data for one stock fails after all retries
- **THEN** the error SHALL be logged with the stock code and error details
- **AND** the import SHALL continue with the next stock
- **AND** the final summary SHALL include the count of failed stocks

### Requirement: Import progress logging
Import scripts SHALL log progress at regular intervals to provide visibility into long-running operations.

#### Scenario: Progress logging during full import
- **WHEN** a full import is running with 5000 stocks
- **THEN** it SHALL log progress every 100 stocks in the format: `"[N/5000] Importing {ts_code} — success={S}, failed={F}"`
- **AND** log a final summary when complete

### Requirement: Full import script for adjustment factors
The system SHALL provide a CLI command `sync-adj-factor` for importing adjustment factors into the `stock_daily.adj_factor` column.

#### Scenario: Run adj factor import via CLI
- **WHEN** `python -m app.data.cli sync-adj-factor` is executed
- **THEN** it SHALL iterate over all listed stocks
- **AND** fetch adjustment factors from Tushare for each stock
- **AND** batch update `stock_daily.adj_factor` for matching rows
- **AND** log progress every 100 stocks
- **AND** print a final summary with success/failed counts

#### Scenario: Run adj factor import with force flag
- **WHEN** `python -m app.data.cli sync-adj-factor --force` is executed
- **THEN** it SHALL re-fetch and overwrite adj factors for ALL stocks regardless of existing data
