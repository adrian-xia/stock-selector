## ADDED Requirements

### Requirement: Batch daily data synchronization
The system SHALL provide a `batch_sync_daily()` async function that synchronizes daily bar data for multiple stocks concurrently, using connection pooling and batch processing.

The function SHALL:
- Accept a list of stock codes and a target date range
- Split the stock list into configurable batch sizes
- Process batches concurrently with configurable concurrency limit
- Reuse BaoStock connections from the connection pool
- Return a summary of successful and failed syncs

#### Scenario: Batch sync with multiple stocks
- **WHEN** `batch_sync_daily(["600519.SH", "000001.SZ", "300750.SZ"], date(2025, 1, 1), date(2025, 1, 31))` is called
- **THEN** the system SHALL fetch daily data for all 3 stocks concurrently and return a summary with success/failure counts

#### Scenario: Batch sync respects concurrency limit
- **WHEN** `batch_sync_daily()` is called with 100 stocks and `BATCH_CONCURRENCY=10`
- **THEN** the system SHALL process at most 10 stocks concurrently at any given time

#### Scenario: Batch sync handles individual failures
- **WHEN** one stock in the batch fails to sync (e.g., network timeout)
- **THEN** the system SHALL continue syncing remaining stocks and include the failure in the summary

#### Scenario: Batch sync uses connection pool
- **WHEN** `batch_sync_daily()` processes multiple stocks
- **THEN** it SHALL acquire connections from the pool, reusing logged-in sessions instead of calling `bs.login()` for each stock

### Requirement: Batch size configuration
The system SHALL allow configuring batch processing parameters via environment variables:
- `DAILY_SYNC_BATCH_SIZE`: Number of stocks to process in each batch (default: 100)
- `DAILY_SYNC_CONCURRENCY`: Maximum number of concurrent sync tasks (default: 10)

#### Scenario: Configure batch size
- **WHEN** `DAILY_SYNC_BATCH_SIZE=50` is set in environment
- **THEN** the system SHALL split the stock list into batches of 50 stocks each

#### Scenario: Configure concurrency
- **WHEN** `DAILY_SYNC_CONCURRENCY=20` is set in environment
- **THEN** the system SHALL process up to 20 stocks concurrently

### Requirement: Progress tracking
The batch sync function SHALL log progress at regular intervals to provide visibility into the sync operation.

#### Scenario: Log batch progress
- **WHEN** `batch_sync_daily()` is processing 1000 stocks in batches of 100
- **THEN** it SHALL log progress after each batch completes (e.g., "Batch 1/10 complete: 98/100 success")

#### Scenario: Log final summary
- **WHEN** `batch_sync_daily()` completes
- **THEN** it SHALL log a final summary with total success/failure counts and elapsed time

### Requirement: Error handling and retry
The batch sync function SHALL implement retry logic for transient failures (network errors, API timeouts) but fail fast for permanent errors (invalid stock code, authentication failure).

#### Scenario: Retry on transient failure
- **WHEN** a stock sync fails with a network timeout
- **THEN** the system SHALL retry up to 3 times with exponential backoff before marking it as failed

#### Scenario: Fail fast on permanent error
- **WHEN** a stock sync fails with "invalid stock code" error
- **THEN** the system SHALL NOT retry and immediately mark it as failed

#### Scenario: Connection pool exhaustion
- **WHEN** all connections in the pool are in use and a new sync task needs a connection
- **THEN** the task SHALL wait for an available connection (up to `BAOSTOCK_POOL_TIMEOUT` seconds) before timing out

### Requirement: Backward compatibility
The batch sync function SHALL be optional - existing code using `DataManager.sync_daily()` for single-stock sync SHALL continue to work without modification.

#### Scenario: Single-stock sync still works
- **WHEN** `DataManager.sync_daily("600519.SH", date(2025, 1, 1), date(2025, 1, 31))` is called
- **THEN** it SHALL sync the single stock using the existing implementation without requiring batch processing
