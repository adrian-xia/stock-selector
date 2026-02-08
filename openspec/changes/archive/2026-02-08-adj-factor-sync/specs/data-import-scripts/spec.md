## ADDED Requirements

### Requirement: Full import script for adjustment factors
The system SHALL provide a CLI command `sync-adj-factor` for importing adjustment factors into the `stock_daily.adj_factor` column.

#### Scenario: Run adj factor import via CLI
- **WHEN** `python -m app.data.cli sync-adj-factor` is executed
- **THEN** it SHALL iterate over all listed stocks
- **AND** fetch adjustment factors from BaoStock for each stock
- **AND** batch update `stock_daily.adj_factor` for matching rows
- **AND** log progress every 100 stocks
- **AND** print a final summary with success/failed counts

#### Scenario: Run adj factor import with force flag
- **WHEN** `python -m app.data.cli sync-adj-factor --force` is executed
- **THEN** it SHALL re-fetch and overwrite adj factors for ALL stocks regardless of existing data

## MODIFIED Requirements

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
