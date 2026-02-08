## MODIFIED Requirements

### Requirement: Daily data sync step
The system SHALL provide a `sync_daily_step(target_date)` async function that syncs daily bar data for all listed stocks.

The function SHALL:
- Query all stocks with status "L" (listed) from the database
- Use batch synchronization with connection pooling for improved performance
- Process stocks in configurable batches with concurrent execution
- Log the count of successfully synced stocks and failed stocks
- NOT raise an exception if individual stocks fail (continue with remaining stocks)
- Log progress at regular intervals during batch processing

#### Scenario: Successful sync
- **WHEN** `sync_daily_step()` is called with a valid trading date
- **THEN** it SHALL sync daily data for all listed stocks using batch processing and log "日线同步完成：成功 N 只，失败 M 只，耗时 Xs"

#### Scenario: Partial failure
- **WHEN** some stocks fail to sync (e.g., API timeout)
- **THEN** the step SHALL continue syncing remaining stocks and log each failure

#### Scenario: Batch sync with connection pool
- **WHEN** `sync_daily_step()` processes 8000+ stocks
- **THEN** it SHALL use the BaoStock connection pool to reuse login sessions across multiple stocks

#### Scenario: Concurrent batch processing
- **WHEN** `sync_daily_step()` is called with `DAILY_SYNC_CONCURRENCY=10`
- **THEN** it SHALL process up to 10 stocks concurrently at any given time

#### Scenario: Progress logging during sync
- **WHEN** `sync_daily_step()` is processing stocks in batches
- **THEN** it SHALL log progress after each batch completes (e.g., "Batch 5/80 complete: 98/100 success")

#### Scenario: Backward compatibility with single-stock sync
- **WHEN** `DataManager.sync_daily(code, target_date, target_date)` is called directly
- **THEN** it SHALL continue to work using the existing single-stock implementation
