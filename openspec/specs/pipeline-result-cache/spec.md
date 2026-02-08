## ADDED Requirements

### Requirement: Cache pipeline result after execution
The system SHALL provide a `cache_pipeline_result(redis_client, trade_date, result)` async function in `app/cache/pipeline_cache.py` that stores the stock selection result as a JSON string in Redis at key `pipeline:result:{trade_date}` with a 48-hour TTL (172800 seconds).

#### Scenario: Cache selection result
- **WHEN** `cache_pipeline_result(redis, "2026-02-07", [...])` is called
- **THEN** the result list SHALL be serialized to JSON and stored at `pipeline:result:2026-02-07`
- **AND** the key SHALL have a 48-hour TTL

#### Scenario: Overwrite existing result
- **WHEN** `cache_pipeline_result()` is called for a date that already has a cached result
- **THEN** the existing value SHALL be overwritten with the new result

### Requirement: Read cached pipeline result
The system SHALL provide a `get_pipeline_result(redis_client, trade_date)` async function that reads the cached selection result from Redis key `pipeline:result:{trade_date}` and deserializes it from JSON.

#### Scenario: Cached result exists
- **WHEN** `get_pipeline_result(redis, "2026-02-07")` is called and the key exists
- **THEN** it SHALL return the deserialized list of stock selection results

#### Scenario: No cached result
- **WHEN** `get_pipeline_result(redis, "2026-02-07")` is called and the key does not exist
- **THEN** it SHALL return `None`

### Requirement: Redis unavailable graceful degradation
All pipeline result cache operations SHALL catch Redis exceptions and degrade gracefully:
- `cache_pipeline_result()`: skip caching and log a warning
- `get_pipeline_result()`: return `None`, allowing the caller to query the database

#### Scenario: Redis down during cache write
- **WHEN** `cache_pipeline_result()` is called and Redis is unreachable
- **THEN** it SHALL log a warning and return without error

#### Scenario: Redis down during cache read
- **WHEN** `get_pipeline_result()` is called and Redis is unreachable
- **THEN** it SHALL return `None`
