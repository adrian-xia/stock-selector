## MODIFIED Requirements

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

## ADDED Requirements

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
