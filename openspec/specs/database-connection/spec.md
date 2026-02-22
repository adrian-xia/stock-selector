## ADDED Requirements

### Requirement: Async SQLAlchemy engine
The system SHALL create an async SQLAlchemy engine using `asyncpg` as the database driver. The engine SHALL be configured with the database URL from application settings.

Configuration:
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql+asyncpg://user:pass@localhost:5432/stock_selector`)
- `DB_POOL_SIZE`: connection pool size (default: 10)
- `DB_MAX_OVERFLOW`: max overflow connections (default: 20)
- `DB_ECHO`: SQL logging (default: `False`)

#### Scenario: Engine creation on startup
- **WHEN** the application starts
- **THEN** an async SQLAlchemy engine SHALL be created with the configured `DATABASE_URL`
- **AND** the connection pool SHALL be initialized with `pool_size=10` and `max_overflow=20` from settings

#### Scenario: Invalid database URL
- **WHEN** the `DATABASE_URL` is invalid or the database is unreachable
- **THEN** the engine creation SHALL raise a clear error with connection details (host, port, database name)

### Requirement: Async session factory
The system SHALL provide an `async_sessionmaker` configured with the async engine. A `get_db_session()` async context manager SHALL be provided for obtaining sessions.

#### Scenario: Session lifecycle in a request
- **WHEN** `async with get_db_session() as session:` is used
- **THEN** a new async session SHALL be created from the session factory
- **AND** the session SHALL be automatically closed when the context manager exits
- **AND** if no exception occurred, the session SHALL be committed
- **AND** if an exception occurred, the session SHALL be rolled back

#### Scenario: Session used in FastAPI dependency
- **WHEN** a FastAPI endpoint declares a dependency on `get_db_session`
- **THEN** it SHALL receive a properly scoped async session for the duration of the request

### Requirement: SQLAlchemy declarative models
The system SHALL define SQLAlchemy ORM models for all V1 tables using the declarative base pattern. Each model SHALL correspond to a table defined in the database-schema spec.

Models SHALL be defined in `app/models/` with one file per domain:
- `app/models/base.py`: declarative base
- `app/models/market.py`: `TradeCalendar`, `Stock`, `StockDaily`, `StockMin`
- `app/models/finance.py`: `FinanceIndicator`
- `app/models/technical.py`: `TechnicalDaily`
- `app/models/flow.py`: `MoneyFlow`, `DragonTiger`
- `app/models/strategy.py`: `Strategy`, `DataSourceConfig`
- `app/models/backtest.py`: `BacktestTask`, `BacktestResult`

#### Scenario: Model-table mapping
- **WHEN** a SQLAlchemy model is defined (e.g., `StockDaily`)
- **THEN** its `__tablename__`, column types, and constraints SHALL match the DDL in the database-schema spec exactly

### Requirement: Alembic migration setup
The system SHALL use Alembic for database schema migrations. An initial migration SHALL be generated that creates all V1 tables.

#### Scenario: Initial migration creates all tables
- **WHEN** `alembic upgrade head` is run against an empty database
- **THEN** all 12 V1 tables SHALL be created with correct columns, types, constraints, and indexes

#### Scenario: Migration is reversible
- **WHEN** `alembic downgrade -1` is run after the initial migration
- **THEN** all tables created by the initial migration SHALL be dropped

### Requirement: Engine disposal on shutdown
The system SHALL dispose of the async engine when the application shuts down, releasing all database connections.

#### Scenario: Graceful shutdown
- **WHEN** the FastAPI application receives a shutdown signal
- **THEN** `engine.dispose()` SHALL be called
- **AND** all pooled connections SHALL be closed

### Requirement: 获取 asyncpg 原始连接
系统 SHALL 提供 `get_raw_connection()` 异步上下文管理器，从 async engine 获取底层 asyncpg 连接用于 COPY 协议操作。

#### Scenario: 获取原始连接
- **WHEN** 使用 `async with get_raw_connection(engine) as raw_conn:`
- **THEN** SHALL 通过 `engine.raw_connection()` 获取底层 asyncpg 连接
- **AND** raw_conn SHALL 支持 `copy_records_to_table()` 方法

#### Scenario: 连接自动释放
- **WHEN** 上下文管理器退出（正常或异常）
- **THEN** 原始连接 SHALL 被释放回连接池
- **AND** 不会发生连接泄漏

### Requirement: TimescaleDB 配置项
系统 SHALL 新增 TimescaleDB 相关配置项：

- `TIMESCALE_ENABLED`: 是否启用 TimescaleDB 功能（默认 True，未安装时自动降级）
- `TIMESCALE_COMPRESS_AFTER_DAYS`: 压缩阈值天数（默认 30）

#### Scenario: 配置项加载
- **WHEN** 应用启动加载配置
- **THEN** TimescaleDB 相关配置项 SHALL 从 .env 文件或环境变量加载
- **AND** 未配置时 SHALL 使用默认值
