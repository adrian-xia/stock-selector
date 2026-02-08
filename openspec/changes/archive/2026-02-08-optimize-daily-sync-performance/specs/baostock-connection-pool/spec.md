## ADDED Requirements

### Requirement: Connection pool for BaoStock sessions
The system SHALL provide a `BaoStockConnectionPool` class that manages a pool of reusable BaoStock login sessions to avoid repeated login/logout operations.

The connection pool SHALL:
- Maintain a configurable number of active BaoStock sessions (default: 5)
- Automatically login when acquiring a connection from the pool
- Reuse existing logged-in sessions when available
- Handle session expiration and automatic re-login
- Support graceful shutdown with proper logout of all sessions
- Be thread-safe for concurrent access from multiple async tasks

#### Scenario: Acquire connection from pool
- **WHEN** a task calls `pool.acquire()` and idle connections are available
- **THEN** the pool SHALL return an existing logged-in session without calling `bs.login()` again

#### Scenario: Acquire connection when pool is full
- **WHEN** a task calls `pool.acquire()` and all connections are in use
- **THEN** the pool SHALL wait until a connection is released or timeout is reached

#### Scenario: Release connection back to pool
- **WHEN** a task calls `pool.release(connection)` after using it
- **THEN** the connection SHALL remain logged in and be returned to the idle pool for reuse

#### Scenario: Handle expired session
- **WHEN** a connection is acquired but the BaoStock session has expired
- **THEN** the pool SHALL automatically call `bs.login()` again before returning the connection

#### Scenario: Pool shutdown
- **WHEN** `pool.close()` is called
- **THEN** the pool SHALL call `bs.logout()` on all active sessions and prevent new acquisitions

#### Scenario: Connection timeout
- **WHEN** `pool.acquire(timeout=10)` is called and no connection becomes available within 10 seconds
- **THEN** the pool SHALL raise a `TimeoutError`

### Requirement: Context manager support
The connection pool SHALL support Python's async context manager protocol for automatic resource cleanup.

#### Scenario: Use connection with async context manager
- **WHEN** a connection is acquired using `async with pool.acquire() as conn:`
- **THEN** the connection SHALL be automatically released back to the pool when the context exits, even if an exception occurs

### Requirement: Pool configuration
The system SHALL allow configuring the connection pool via environment variables:
- `BAOSTOCK_POOL_SIZE`: Maximum number of concurrent connections (default: 5)
- `BAOSTOCK_POOL_TIMEOUT`: Maximum wait time in seconds when acquiring a connection (default: 30)
- `BAOSTOCK_SESSION_TTL`: Session time-to-live in seconds before re-login (default: 3600)

#### Scenario: Configure pool size
- **WHEN** `BAOSTOCK_POOL_SIZE=10` is set in environment
- **THEN** the pool SHALL maintain up to 10 concurrent BaoStock sessions

#### Scenario: Configure acquisition timeout
- **WHEN** `BAOSTOCK_POOL_TIMEOUT=60` is set in environment
- **THEN** `pool.acquire()` SHALL wait up to 60 seconds before raising `TimeoutError`

### Requirement: Pool health monitoring
The connection pool SHALL provide a `health_check()` method that verifies all connections in the pool are functional.

#### Scenario: Health check on healthy pool
- **WHEN** `pool.health_check()` is called and all sessions are logged in
- **THEN** it SHALL return `True`

#### Scenario: Health check detects dead sessions
- **WHEN** `pool.health_check()` is called and some sessions have expired
- **THEN** it SHALL attempt to re-login those sessions and return `False` if re-login fails
