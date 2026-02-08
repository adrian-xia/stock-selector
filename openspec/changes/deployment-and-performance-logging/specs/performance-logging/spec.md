## ADDED Requirements

### Requirement: Detailed batch sync performance logging
The batch daily sync function SHALL log detailed performance metrics for each batch and individual stock.

The logging SHALL include:
- Total number of stocks to sync
- Batch size and concurrency settings
- Per-batch timing (batch number, success count, failure count, elapsed time)
- Per-stock timing for failed stocks (to identify slow stocks)
- Overall summary (total success, total failures, total elapsed time, average time per stock)

#### Scenario: Log batch progress
- **WHEN** batch sync processes 8000 stocks in batches of 100
- **THEN** system SHALL log after each batch: "[批量同步] Batch 5/80 完成：成功 98/100，耗时 15.2s"

#### Scenario: Log overall summary
- **WHEN** batch sync completes
- **THEN** system SHALL log: "[批量同步] 完成：成功 7950 只，失败 50 只，总耗时 1200s，平均 0.15s/只"

#### Scenario: Log slow stocks
- **WHEN** individual stocks take longer than a threshold (e.g., 5 seconds)
- **THEN** system SHALL log a warning: "[批量同步] 慢速股票：600519.SH 耗时 8.3s"

#### Scenario: Log failed stocks with reason
- **WHEN** stocks fail to sync
- **THEN** system SHALL log: "[批量同步] 失败：600000.SH - API timeout after 30s"

#### Scenario: Log fine-grained timing for sync_daily
- **WHEN** `DataManager.sync_daily()` syncs a single stock
- **THEN** system SHALL log timing breakdown at DEBUG level: "[sync_daily] 600519.SH: API=2.5s, 清洗=0.01s, 入库=0.3s"

#### Scenario: Identify performance bottleneck in sync_daily
- **WHEN** analyzing sync_daily logs
- **THEN** users SHALL be able to determine whether API calls, data cleaning, or database writes are the bottleneck

### Requirement: Technical indicator calculation performance logging
The technical indicator calculation function SHALL log detailed timing for each indicator type.

The logging SHALL include:
- Total number of stocks to process
- Per-indicator timing (indicator name, number of stocks processed, elapsed time)
- Overall summary (total indicators calculated, total elapsed time)

#### Scenario: Log per-indicator timing
- **WHEN** technical indicators are calculated for 8000 stocks
- **THEN** system SHALL log for each indicator: "[技术指标] MA 计算完成：8000 只股票，耗时 12.5s"

#### Scenario: Log overall indicator summary
- **WHEN** all technical indicators are calculated
- **THEN** system SHALL log: "[技术指标] 完成：计算 15 个指标，总耗时 180s"

#### Scenario: Log slow indicator calculations
- **WHEN** an indicator takes longer than expected (e.g., >30 seconds)
- **THEN** system SHALL log a warning: "[技术指标] 慢速指标：MACD 耗时 45.2s"

### Requirement: Cache refresh performance logging
The cache refresh function SHALL log detailed timing for cache operations.

The logging SHALL include:
- Number of stocks to refresh
- Cache hit/miss statistics
- Per-operation timing (cache read, cache write, database query)
- Overall summary (total stocks refreshed, total elapsed time)

#### Scenario: Log cache refresh progress
- **WHEN** cache refresh processes stocks in batches
- **THEN** system SHALL log: "[缓存刷新] 进度：500/8000 只股票已刷新，耗时 25s"

#### Scenario: Log cache hit rate
- **WHEN** cache refresh completes
- **THEN** system SHALL log: "[缓存刷新] 完成：8000 只股票，缓存命中率 85%，耗时 120s"

#### Scenario: Log slow cache operations
- **WHEN** cache operations take longer than expected
- **THEN** system SHALL log a warning: "[缓存刷新] 慢速操作：Redis 写入耗时 5.2s"

### Requirement: Scheduler job performance logging
Each scheduler job SHALL log start time, end time, and elapsed time.

#### Scenario: Log job start
- **WHEN** a scheduled job starts
- **THEN** system SHALL log: "[盘后链路] 开始：2026-02-09"

#### Scenario: Log job completion
- **WHEN** a scheduled job completes
- **THEN** system SHALL log: "[盘后链路] 完成：2026-02-09，总耗时 1800s (30分钟)"

#### Scenario: Log job failure
- **WHEN** a scheduled job fails
- **THEN** system SHALL log: "[盘后链路] 失败：2026-02-09，错误：Database connection timeout"

### Requirement: Performance metrics aggregation
The system SHALL provide a function to aggregate and analyze performance metrics from logs.

#### Scenario: Extract timing metrics from logs
- **WHEN** user runs a log analysis script
- **THEN** system SHALL extract timing metrics for each job type and generate a summary report

#### Scenario: Identify performance bottlenecks
- **WHEN** log analysis detects operations consistently taking >50% of total time
- **THEN** system SHALL flag them as bottlenecks in the report

### Requirement: Configurable log verbosity
The system SHALL support configurable log verbosity for performance logging.

#### Scenario: Detailed logging mode
- **WHEN** `PERFORMANCE_LOG_LEVEL=DEBUG` is configured
- **THEN** system SHALL log per-stock timing for all operations

#### Scenario: Summary logging mode
- **WHEN** `PERFORMANCE_LOG_LEVEL=INFO` is configured (default)
- **THEN** system SHALL log only batch summaries and overall timing

#### Scenario: Minimal logging mode
- **WHEN** `PERFORMANCE_LOG_LEVEL=WARNING` is configured
- **THEN** system SHALL log only slow operations and failures
