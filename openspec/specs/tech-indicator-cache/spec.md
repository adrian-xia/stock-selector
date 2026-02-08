## ADDED Requirements

### Requirement: Single stock indicator cache read
The system SHALL provide a `TechIndicatorCache` class in `app/cache/tech_cache.py` with a `get_latest(ts_code)` async method that implements Cache-Aside pattern:
1. Query Redis Hash at key `tech:{ts_code}:latest`
2. On cache hit, return the indicator dictionary
3. On cache miss, query the `technical_daily` table for the latest row, backfill Redis with 25-hour TTL (90000 seconds), and return the result

The Hash field names SHALL match the `technical_daily` table column names exactly: `ma5`, `ma10`, `ma20`, `ma60`, `ma120`, `ma250`, `macd_dif`, `macd_dea`, `macd_hist`, `kdj_k`, `kdj_d`, `kdj_j`, `rsi6`, `rsi12`, `rsi24`, `boll_upper`, `boll_mid`, `boll_lower`, `vol_ma5`, `vol_ma10`, `vol_ratio`, `atr14`, `trade_date`.

#### Scenario: Cache hit
- **WHEN** `get_latest("600519.SH")` is called and Redis has the key `tech:600519.SH:latest`
- **THEN** it SHALL return the indicator dictionary from Redis without querying the database

#### Scenario: Cache miss with DB fallback
- **WHEN** `get_latest("600519.SH")` is called and Redis does not have the key
- **THEN** it SHALL query `technical_daily` for the latest row of that stock
- **AND** backfill the result into Redis with 25-hour TTL
- **AND** return the indicator dictionary

#### Scenario: No data in DB
- **WHEN** `get_latest("999999.SH")` is called and neither Redis nor DB has data
- **THEN** it SHALL return `None`

### Requirement: Batch indicator cache read
The `TechIndicatorCache` class SHALL provide a `get_batch(ts_codes)` async method that uses Redis Pipeline to batch-read multiple stocks' indicators:
1. Issue `HGETALL` for all requested keys via a single Redis Pipeline
2. Collect cache misses
3. For each miss, call `get_latest()` to query DB and backfill

#### Scenario: All cache hits
- **WHEN** `get_batch(["600519.SH", "000001.SZ"])` is called and both keys exist in Redis
- **THEN** it SHALL return both indicators from Redis using a single Pipeline round-trip

#### Scenario: Partial cache miss
- **WHEN** `get_batch(["600519.SH", "000001.SZ"])` is called and only one key exists in Redis
- **THEN** it SHALL return the cached one from Redis and query DB for the missing one
- **AND** backfill the missing one into Redis

### Requirement: Full cache refresh
The system SHALL provide a `refresh_all_tech_cache(redis_client, session_factory)` async function that:
1. Queries all stocks' latest technical indicators from `technical_daily` using `DISTINCT ON (ts_code)`
2. Writes all indicators to Redis using Pipeline in batches (configurable batch size, default 500)
3. Sets 25-hour TTL on each key

#### Scenario: Full refresh after market close
- **WHEN** `refresh_all_tech_cache()` is called
- **THEN** it SHALL write all stocks' latest indicators to Redis
- **AND** log "技术指标缓存刷新完成: N 只股票"

#### Scenario: Batch pipeline execution
- **WHEN** refreshing 5000+ stocks
- **THEN** the function SHALL execute Redis Pipeline every `CACHE_REFRESH_BATCH_SIZE` entries to avoid oversized pipelines

### Requirement: Cache warmup on startup
The system SHALL provide a `warmup_cache(redis_client, session_factory)` async function that:
1. Checks if Redis already has sufficient cached data (>= 100 `tech:*:latest` keys)
2. If insufficient, calls `refresh_all_tech_cache()` to populate the cache
3. Is called during FastAPI lifespan startup when `CACHE_WARMUP_ON_STARTUP` is `True`

#### Scenario: Cold start warmup
- **WHEN** the application starts and Redis has no cached indicator data
- **THEN** it SHALL execute full cache refresh and log "缓存预热完成: N 只股票"

#### Scenario: Warm start skip
- **WHEN** the application starts and Redis already has >= 100 cached indicator keys
- **THEN** it SHALL skip the refresh and log "Redis 已有缓存数据，跳过预热"

#### Scenario: Warmup disabled
- **WHEN** `CACHE_WARMUP_ON_STARTUP` is `False`
- **THEN** the warmup step SHALL be skipped entirely

### Requirement: Redis unavailable graceful degradation
All cache read and write operations SHALL catch Redis exceptions (connection errors, timeouts) and degrade gracefully:
- Read operations: return `None` or empty result, allowing the caller to fall back to DB
- Write operations: skip the cache write and log a warning
- Warmup: skip and log a warning

The system SHALL NOT raise exceptions to callers due to Redis failures.

#### Scenario: Redis down during read
- **WHEN** `get_latest()` is called and Redis is unreachable
- **THEN** it SHALL query the database directly and return the result without caching

#### Scenario: Redis down during write
- **WHEN** `refresh_all_tech_cache()` is called and Redis is unreachable
- **THEN** it SHALL log a warning and return without error
