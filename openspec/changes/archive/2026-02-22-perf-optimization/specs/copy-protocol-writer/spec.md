## ADDED Requirements

### Requirement: COPY 协议批量写入函数
系统 SHALL 提供 `copy_insert(session, table, rows, batch_size=50000)` 异步函数，使用 PostgreSQL COPY 协议将数据批量写入目标表。该函数 SHALL 采用临时表 + COPY + UPSERT 三步法实现幂等写入。

步骤：
1. 创建与目标表同结构的临时表 `_tmp_{table_name}`（ON COMMIT DROP）
2. 通过 asyncpg `copy_records_to_table()` 将数据 COPY 到临时表
3. 从临时表 INSERT INTO 目标表，使用 ON CONFLICT DO UPDATE（raw 表）或 ON CONFLICT DO NOTHING（业务表）
4. 提交事务（临时表自动清理）

#### Scenario: COPY 写入 raw 表（UPSERT 模式）
- **WHEN** 调用 `copy_insert(session, raw_tushare_daily, rows, conflict="update")`
- **THEN** 数据 SHALL 通过 COPY 协议写入临时表，再 UPSERT 到 raw_tushare_daily
- **AND** 已存在的行 SHALL 被更新，新行 SHALL 被插入

#### Scenario: COPY 写入业务表（INSERT IGNORE 模式）
- **WHEN** 调用 `copy_insert(session, stock_daily, rows, conflict="nothing")`
- **THEN** 数据 SHALL 通过 COPY 协议写入临时表，再 INSERT ON CONFLICT DO NOTHING 到 stock_daily
- **AND** 已存在的行 SHALL 被跳过

#### Scenario: 大批量数据自动分批
- **WHEN** 调用 `copy_insert(session, table, rows)` 且 rows 超过 50000 行
- **THEN** 数据 SHALL 按 50000 行一批分批 COPY，每批使用独立临时表

#### Scenario: COPY 失败自动降级
- **WHEN** COPY 协议写入失败（如 asyncpg 连接异常）
- **THEN** SHALL 自动降级到现有 `batch_insert()` 或 `_upsert_raw()` 方式
- **AND** SHALL 记录 WARNING 日志说明降级原因

### Requirement: 获取 asyncpg 原始连接
系统 SHALL 提供 `get_raw_connection()` 异步上下文管理器，从 SQLAlchemy async engine 获取底层 asyncpg 连接，用于 COPY 操作。

#### Scenario: 获取并释放原始连接
- **WHEN** 使用 `async with get_raw_connection() as raw_conn:`
- **THEN** SHALL 获取底层 asyncpg 连接
- **AND** 上下文退出时 SHALL 自动释放连接回连接池

#### Scenario: 连接异常时安全释放
- **WHEN** COPY 操作过程中发生异常
- **THEN** 原始连接 SHALL 在 finally 块中被释放，不会泄漏

### Requirement: COPY 写入性能日志
系统 SHALL 记录 COPY 写入的性能指标，包括行数、耗时、是否降级。

#### Scenario: 正常 COPY 写入日志
- **WHEN** COPY 写入成功完成
- **THEN** SHALL 记录 INFO 日志：表名、行数、耗时、写入速率（行/秒）

#### Scenario: 降级写入日志
- **WHEN** COPY 降级到 INSERT 方式
- **THEN** SHALL 记录 WARNING 日志：表名、降级原因、fallback 方式
