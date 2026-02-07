## ADDED Requirements

### Requirement: compute-indicators CLI command
The system SHALL provide a `compute-indicators` CLI command that triggers full market technical indicator computation.

The command SHALL be registered as a Click command in `app/data/cli.py` and accessible via `python -m app.data.cli compute-indicators`.

#### Scenario: Run full computation
- **WHEN** `compute-indicators` is executed without arguments
- **THEN** it SHALL call `compute_all_stocks()` for all listed stocks
- **AND** print a summary showing total/success/failed counts and elapsed time
- **AND** exit with code 0 on success

#### Scenario: Run full computation with failure
- **WHEN** `compute-indicators` is executed and a database connection error occurs
- **THEN** it SHALL print the error message to stderr
- **AND** exit with code 1

### Requirement: update-indicators CLI command
The system SHALL provide an `update-indicators` CLI command that triggers incremental (latest trading day) technical indicator computation.

#### Scenario: Run incremental update
- **WHEN** `update-indicators` is executed without arguments
- **THEN** it SHALL call `compute_incremental()` for the latest trading day
- **AND** print a summary showing the target date, total/success/failed counts
- **AND** exit with code 0 on success

#### Scenario: Run incremental update with specific date
- **WHEN** `update-indicators --date 2026-02-06` is executed
- **THEN** it SHALL call `compute_incremental(target_date=date(2026, 2, 6))`
- **AND** compute indicators for the specified date

#### Scenario: Run incremental update with progress logging
- **WHEN** `update-indicators` is executed
- **THEN** it SHALL log progress every 500 stocks processed (e.g., "Processed 500/5000 stocks...")
