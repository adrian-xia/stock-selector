## ADDED Requirements

### Requirement: Redis async client initialization
The system SHALL provide an `init_redis()` async function in `app/cache/redis_client.py` that creates a `redis.asyncio.Redis` connection instance using the application's Redis configuration (`redis_host`, `redis_port`, `redis_db`, `redis_password`).

The connection SHALL use `hiredis` as the protocol parser for performance optimization.

The initialized client SHALL be stored in a module-level variable accessible via `get_redis()`.

#### Scenario: Successful Redis connection
- **WHEN** `init_redis()` is called and Redis is available
- **THEN** a `redis.asyncio.Redis` instance SHALL be created and stored
- **AND** `get_redis()` SHALL return the active Redis instance

#### Scenario: Redis unavailable at startup
- **WHEN** `init_redis()` is called and Redis is not reachable
- **THEN** the function SHALL catch the connection exception
- **AND** log a warning message "Redis 连接失败，缓存功能降级"
- **AND** the application SHALL continue to start normally without Redis

### Requirement: Redis client retrieval
The system SHALL provide a `get_redis()` function that returns the initialized `redis.asyncio.Redis` instance, or `None` if Redis was not successfully initialized.

Callers SHALL use the return value to determine whether caching is available.

#### Scenario: Redis initialized
- **WHEN** `get_redis()` is called after successful `init_redis()`
- **THEN** it SHALL return the active `redis.asyncio.Redis` instance

#### Scenario: Redis not initialized
- **WHEN** `get_redis()` is called when Redis initialization failed or was not attempted
- **THEN** it SHALL return `None`

### Requirement: Redis client shutdown
The system SHALL provide a `close_redis()` async function that gracefully closes the Redis connection and resets the module-level client to `None`.

#### Scenario: Graceful shutdown
- **WHEN** `close_redis()` is called with an active Redis connection
- **THEN** the connection SHALL be closed
- **AND** `get_redis()` SHALL return `None` after closure

#### Scenario: Shutdown without active connection
- **WHEN** `close_redis()` is called when no Redis connection exists
- **THEN** the function SHALL complete without error

### Requirement: FastAPI lifespan integration
The system SHALL call `init_redis()` during FastAPI lifespan startup and `close_redis()` during shutdown, integrating with the existing lifespan handler in `app/main.py`.

#### Scenario: Application startup with Redis
- **WHEN** the FastAPI application starts
- **THEN** `init_redis()` SHALL be called before the application begins serving requests

#### Scenario: Application shutdown
- **WHEN** the FastAPI application shuts down
- **THEN** `close_redis()` SHALL be called to release the Redis connection
