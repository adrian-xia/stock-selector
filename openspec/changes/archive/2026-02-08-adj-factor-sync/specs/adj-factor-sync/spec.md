## ADDED Requirements

### Requirement: Adj factor data retrieval from BaoStock
The system SHALL provide a method to fetch adjustment factors (复权因子) from BaoStock's `query_adjust_factor()` API for a given stock code and date range.

The method SHALL:
- Accept a standard stock code (e.g., `600519.SH`), start date, and end date
- Return a list of dicts containing `ts_code`, `trade_date`, and `adj_factor` (前复权因子)
- Use the `foreAdjustFactor` field from BaoStock's response as the `adj_factor` value
- Reuse the existing retry, rate limiting, and thread executor mechanisms of `BaoStockClient`

#### Scenario: Fetch adj factors for a stock with dividends
- **WHEN** `fetch_adj_factor("000001.SZ", date(2024, 1, 1), date(2024, 12, 31))` is called
- **THEN** it SHALL return a list of dicts, one per trading day
- **AND** each dict SHALL contain keys: `ts_code` (str), `trade_date` (str), `adj_factor` (Decimal)
- **AND** the `adj_factor` values SHALL change on ex-dividend dates

#### Scenario: Fetch adj factors for a stock with no corporate actions
- **WHEN** `fetch_adj_factor("600519.SH", date(2025, 1, 1), date(2025, 3, 31))` is called for a period with no dividends or splits
- **THEN** all returned `adj_factor` values SHALL be identical

#### Scenario: BaoStock adj factor API failure
- **WHEN** the BaoStock `query_adjust_factor()` call fails
- **THEN** the system SHALL retry with exponential backoff per the existing retry policy
- **AND** raise `DataSourceError` if all retries are exhausted

### Requirement: Batch update adj_factor in stock_daily
The system SHALL provide a function to batch update the `adj_factor` column in the `stock_daily` table for a given stock code.

The function SHALL:
- Accept a stock code and a list of `(trade_date, adj_factor)` pairs
- Execute a batch `UPDATE stock_daily SET adj_factor = :val WHERE ts_code = :code AND trade_date = :date`
- Commit in a single transaction per stock
- Automatically chunk updates to respect the asyncpg 32767 parameter limit

#### Scenario: Update adj factors for a stock
- **WHEN** batch update is called with 2000 date-factor pairs for stock `600519.SH`
- **THEN** all 2000 rows in `stock_daily` SHALL have their `adj_factor` updated
- **AND** the operation SHALL complete in a single transaction

#### Scenario: No matching rows
- **WHEN** batch update is called with dates that do not exist in `stock_daily`
- **THEN** the update SHALL complete without error (zero rows affected)

### Requirement: Full adj factor import CLI command
The system SHALL provide a CLI command `sync-adj-factor` that imports adjustment factors for all listed stocks.

The command SHALL:
- Query all listed stocks from the `stocks` table
- Skip stocks that already have `adj_factor` populated (all trading days have non-NULL values) unless `--force` is specified
- For each stock, fetch adj factors from BaoStock and batch update `stock_daily`
- Log progress every 100 stocks
- Print a final summary with success/failed counts

#### Scenario: First-time full import
- **WHEN** `sync-adj-factor` is run and no stocks have `adj_factor` populated
- **THEN** it SHALL fetch and update adj factors for all listed stocks
- **AND** log progress in the format `[N/total] Syncing adj_factor for {ts_code}`

#### Scenario: Re-run after partial completion
- **WHEN** `sync-adj-factor` is re-run after a previous partial run
- **THEN** it SHALL skip stocks that already have `adj_factor` fully populated
- **AND** only process stocks with NULL `adj_factor` values

#### Scenario: Force refresh
- **WHEN** `sync-adj-factor --force` is run
- **THEN** it SHALL re-fetch and overwrite adj factors for ALL stocks regardless of existing data

#### Scenario: Single stock failure during import
- **WHEN** fetching adj factors for one stock fails after all retries
- **THEN** the error SHALL be logged with the stock code
- **AND** the import SHALL continue with the next stock

### Requirement: Incremental adj factor sync
The system SHALL automatically sync the current day's adjustment factor as part of the daily incremental sync flow (`sync-daily`).

After daily bar data is synced for each stock, the system SHALL:
- Fetch the adj factor for the synced date
- Update `stock_daily.adj_factor` for that stock and date

#### Scenario: Daily sync includes adj factor
- **WHEN** `sync-daily` is run on a trading day
- **THEN** after syncing daily bars for each stock, it SHALL also fetch and update the adj factor for that day

#### Scenario: Daily sync on non-trading day
- **WHEN** `sync-daily` is run on a non-trading day
- **THEN** it SHALL skip both daily bar sync and adj factor sync
