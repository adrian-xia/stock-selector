## ADDED Requirements

### Requirement: Run chain CLI command
The system SHALL provide a `run-chain` CLI command that manually triggers the post-market chain for a specified date.

Arguments:
- `--date` (optional): Target date in ISO format (default: today)

#### Scenario: Manual chain execution
- **WHEN** user runs `python -m app.scheduler.cli run-chain`
- **THEN** it SHALL execute the full post-market chain for today's date

#### Scenario: Chain for specific date
- **WHEN** user runs `python -m app.scheduler.cli run-chain --date 2024-06-15`
- **THEN** it SHALL execute the post-market chain for 2024-06-15

#### Scenario: Non-trading day warning
- **WHEN** user runs `run-chain` for a non-trading day
- **THEN** it SHALL print a warning and skip execution (same as scheduled behavior)

### Requirement: Run single job CLI command
The system SHALL provide a `run-job` CLI command that manually triggers a single step of the chain.

Arguments:
- `job_name` (required): One of `sync-daily`, `indicators`, `pipeline`, `sync-stocks`
- `--date` (optional): Target date in ISO format (default: today)

#### Scenario: Run single sync step
- **WHEN** user runs `python -m app.scheduler.cli run-job sync-daily`
- **THEN** it SHALL execute only the daily sync step for today

#### Scenario: Run indicators step
- **WHEN** user runs `python -m app.scheduler.cli run-job indicators --date 2024-06-15`
- **THEN** it SHALL execute only the indicator computation for 2024-06-15

#### Scenario: Invalid job name
- **WHEN** user runs `python -m app.scheduler.cli run-job unknown-job`
- **THEN** it SHALL print an error listing available job names
