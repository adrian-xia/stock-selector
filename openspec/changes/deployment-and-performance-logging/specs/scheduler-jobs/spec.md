## MODIFIED Requirements

### Requirement: Daily data sync step
The system SHALL provide a `sync_daily_step(target_date)` async function that syncs daily bar data for all listed stocks with enhanced performance logging.

The function SHALL:
- Query all stocks with status "L" (listed) from the database
- Use batch synchronization with connection pooling for improved performance
- Process stocks in configurable batches with concurrent execution
- Log detailed performance metrics including per-batch timing and overall summary
- Log slow stocks that exceed a timing threshold
- Log the count of successfully synced stocks and failed stocks with reasons
- NOT raise an exception if individual stocks fail (continue with remaining stocks)
- Log progress at regular intervals during batch processing

#### Scenario: Successful sync
- **WHEN** `sync_daily_step()` is called with a valid trading date
- **THEN** it SHALL sync daily data for all listed stocks using batch processing and log "日线同步完成：成功 N 只，失败 M 只，耗时 Xs，平均 Ys/只"

#### Scenario: Partial failure
- **WHEN** some stocks fail to sync (e.g., API timeout)
- **THEN** the step SHALL continue syncing remaining stocks and log each failure with reason

#### Scenario: Batch sync with connection pool
- **WHEN** `sync_daily_step()` processes 8000+ stocks
- **THEN** it SHALL use the BaoStock connection pool to reuse login sessions across multiple stocks

#### Scenario: Concurrent batch processing
- **WHEN** `sync_daily_step()` is called with `DAILY_SYNC_CONCURRENCY=10`
- **THEN** it SHALL process up to 10 stocks concurrently at any given time

#### Scenario: Progress logging during sync
- **WHEN** `sync_daily_step()` is processing stocks in batches
- **THEN** it SHALL log progress after each batch completes (e.g., "Batch 5/80 complete: 98/100 success, 15.2s")

#### Scenario: Slow stock detection
- **WHEN** individual stocks take longer than 5 seconds to sync
- **THEN** system SHALL log a warning with the stock code and elapsed time

#### Scenario: Backward compatibility with single-stock sync
- **WHEN** `DataManager.sync_daily(code, target_date, target_date)` is called directly
- **THEN** it SHALL continue to work using the existing single-stock implementation

## ADDED Requirements

### Requirement: Technical indicator calculation step with performance logging
The system SHALL provide an `indicator_step(target_date)` async function that calculates technical indicators with detailed performance logging.

The function SHALL:
- Calculate technical indicators for all listed stocks
- Log per-indicator timing (indicator name, stock count, elapsed time)
- Log overall summary (total indicators, total elapsed time)
- Log warnings for slow indicator calculations

#### Scenario: Log per-indicator timing
- **WHEN** `indicator_step()` calculates indicators
- **THEN** it SHALL log timing for each indicator type (e.g., "MA 计算完成：8000 只股票，耗时 12.5s")

#### Scenario: Log overall summary
- **WHEN** `indicator_step()` completes
- **THEN** it SHALL log: "[技术指标] 完成：计算 N 个指标，总耗时 Xs"

### Requirement: Cache refresh step with performance logging
The system SHALL provide a `cache_refresh_step(target_date)` async function that refreshes cache with detailed performance logging.

The function SHALL:
- Refresh technical indicator cache for all listed stocks
- Log cache hit/miss statistics
- Log progress at regular intervals
- Log overall summary with cache hit rate and elapsed time

#### Scenario: Log cache refresh progress
- **WHEN** `cache_refresh_step()` processes stocks
- **THEN** it SHALL log progress periodically (e.g., "进度：500/8000 只股票已刷新")

#### Scenario: Log cache hit rate
- **WHEN** `cache_refresh_step()` completes
- **THEN** it SHALL log: "[缓存刷新] 完成：N 只股票，缓存命中率 X%，耗时 Ys"
