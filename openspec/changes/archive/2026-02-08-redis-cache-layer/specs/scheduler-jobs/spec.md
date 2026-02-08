## MODIFIED Requirements

### Requirement: Post-market chain execution
The system SHALL provide a `run_post_market_chain(target_date)` async function that executes the post-market pipeline in serial order:
1. Trading day check — skip entire chain if not a trading day
2. Daily data sync — sync daily bars for all listed stocks
3. Technical indicator calculation — incremental compute for target_date
4. **Cache refresh** — refresh all technical indicator caches in Redis
5. Strategy pipeline execution — run all registered strategies

Each step SHALL log its start time, completion time, and result summary.

#### Scenario: Full chain on trading day
- **WHEN** `run_post_market_chain()` is called on a trading day
- **THEN** it SHALL execute sync → indicators → **cache refresh** → pipeline in order and log completion

#### Scenario: Chain skipped on non-trading day
- **WHEN** `run_post_market_chain()` is called on a weekend or holiday
- **THEN** it SHALL log "非交易日，跳过盘后任务" and return without executing any step

#### Scenario: Chain stops on step failure
- **WHEN** a step in the chain raises an exception
- **THEN** subsequent steps SHALL NOT execute, and the error SHALL be logged with full traceback

#### Scenario: Cache refresh failure does not block pipeline
- **WHEN** the cache refresh step fails (e.g., Redis unavailable)
- **THEN** the strategy pipeline step SHALL still execute
- **AND** the cache refresh failure SHALL be logged as a warning

## ADDED Requirements

### Requirement: Cache refresh step
The system SHALL provide a `cache_refresh_step(target_date)` async function that calls `refresh_all_tech_cache()` to refresh all technical indicator caches in Redis after indicator calculation completes.

The cache refresh step SHALL be treated as non-critical: if it fails, the chain SHALL continue to the next step (strategy pipeline) and log a warning instead of raising an exception.

#### Scenario: Successful cache refresh
- **WHEN** `cache_refresh_step()` is called after indicator computation
- **THEN** it SHALL call `refresh_all_tech_cache()` and log "缓存刷新完成: N 只股票"

#### Scenario: Cache refresh failure
- **WHEN** `cache_refresh_step()` is called and Redis is unavailable
- **THEN** it SHALL log a warning "缓存刷新失败，策略管道将回源数据库" and return without raising
