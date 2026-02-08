## ADDED Requirements

### Requirement: Post-market chain execution
The system SHALL provide a `run_post_market_chain(target_date)` async function that executes the post-market pipeline in serial order:
1. Trading day check — skip entire chain if not a trading day
2. Daily data sync — sync daily bars for all listed stocks
3. Technical indicator calculation — incremental compute for target_date
4. Strategy pipeline execution — run all registered strategies

Each step SHALL log its start time, completion time, and result summary.

#### Scenario: Full chain on trading day
- **WHEN** `run_post_market_chain()` is called on a trading day
- **THEN** it SHALL execute sync → indicators → pipeline in order and log completion

#### Scenario: Chain skipped on non-trading day
- **WHEN** `run_post_market_chain()` is called on a weekend or holiday
- **THEN** it SHALL log "非交易日，跳过盘后任务" and return without executing any step

#### Scenario: Chain stops on step failure
- **WHEN** a step in the chain raises an exception
- **THEN** subsequent steps SHALL NOT execute, and the error SHALL be logged with full traceback

### Requirement: Daily data sync step
The system SHALL provide a `sync_daily_step(target_date)` async function that syncs daily bar data for all listed stocks.

The function SHALL:
- Query all stocks with status "L" (listed) from the database
- Call `DataManager.sync_daily(code, target_date, target_date)` for each stock
- Log the count of successfully synced stocks and failed stocks
- NOT raise an exception if individual stocks fail (continue with remaining stocks)

#### Scenario: Successful sync
- **WHEN** `sync_daily_step()` is called with a valid trading date
- **THEN** it SHALL sync daily data for all listed stocks and log "日线同步完成：成功 N 只，失败 M 只"

#### Scenario: Partial failure
- **WHEN** some stocks fail to sync (e.g., API timeout)
- **THEN** the step SHALL continue syncing remaining stocks and log each failure

### Requirement: Technical indicator step
The system SHALL provide an `indicator_step(target_date)` async function that calls `compute_incremental(session_factory, target_date)` to calculate technical indicators for the target date.

#### Scenario: Indicators computed
- **WHEN** `indicator_step()` is called after daily sync
- **THEN** it SHALL call `compute_incremental()` and log the result summary

### Requirement: Strategy pipeline step
The system SHALL provide a `pipeline_step(target_date)` async function that calls `execute_pipeline()` with all registered strategies.

The function SHALL:
- Get all strategy names from `StrategyFactory.get_all()`
- Call `execute_pipeline(session_factory, strategy_names, target_date, top_n=50)`
- Log the number of picks and elapsed time

#### Scenario: Pipeline executed with all strategies
- **WHEN** `pipeline_step()` is called after indicator computation
- **THEN** it SHALL execute the pipeline with all 12 strategies and log "策略管道完成：筛选出 N 只，耗时 Xms"

### Requirement: Weekend stock list sync
The system SHALL provide a `sync_stock_list_job()` async function that calls `DataManager.sync_stock_list()` to refresh the full stock list.

#### Scenario: Stock list synced on weekend
- **WHEN** `sync_stock_list_job()` is triggered on Saturday
- **THEN** it SHALL sync the stock list and log the result

### Requirement: Trading day check
The system SHALL check whether the target date is a trading day before executing market-related jobs by calling `DataManager.is_trade_day(target_date)`.

#### Scenario: Trading day confirmed
- **WHEN** `is_trade_day()` returns True for the target date
- **THEN** the post-market chain SHALL proceed with execution

#### Scenario: Non-trading day detected
- **WHEN** `is_trade_day()` returns False for the target date
- **THEN** the post-market chain SHALL skip execution and log the reason
