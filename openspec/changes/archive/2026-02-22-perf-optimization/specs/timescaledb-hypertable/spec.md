## ADDED Requirements

### Requirement: TimescaleDB 扩展检测
系统 SHALL 提供 `is_timescaledb_available(engine)` 异步函数，检测当前 PostgreSQL 实例是否安装了 TimescaleDB 扩展。

#### Scenario: TimescaleDB 已安装
- **WHEN** 调用 `is_timescaledb_available(engine)` 且数据库已安装 TimescaleDB
- **THEN** SHALL 返回 True

#### Scenario: TimescaleDB 未安装
- **WHEN** 调用 `is_timescaledb_available(engine)` 且数据库未安装 TimescaleDB
- **THEN** SHALL 返回 False
- **AND** SHALL 记录 INFO 日志提示 TimescaleDB 不可用，将使用普通表

### Requirement: 超表迁移
Alembic 迁移脚本 SHALL 将 `stock_daily` 和 `technical_daily` 表转换为 TimescaleDB 超表。迁移 SHALL 检测 TimescaleDB 是否可用，不可用时跳过。

配置：
- 分区维度：`trade_date`
- Chunk 间隔：1 个月（`interval '1 month'`）

#### Scenario: TimescaleDB 可用时执行迁移
- **WHEN** 执行 `alembic upgrade head` 且 TimescaleDB 已安装
- **THEN** SHALL 执行 `CREATE EXTENSION IF NOT EXISTS timescaledb`
- **AND** SHALL 将 stock_daily 转为超表：`create_hypertable('stock_daily', 'trade_date', chunk_time_interval => interval '1 month', migrate_data => true)`
- **AND** SHALL 将 technical_daily 转为超表（同样配置）

#### Scenario: TimescaleDB 不可用时跳过
- **WHEN** 执行 `alembic upgrade head` 且 TimescaleDB 未安装
- **THEN** SHALL 跳过超表转换，记录 WARNING 日志
- **AND** 表 SHALL 保持为普通表，不影响其他功能

#### Scenario: 迁移回滚
- **WHEN** 执行 `alembic downgrade` 回滚此迁移
- **THEN** SHALL 记录 WARNING 日志说明超表转换不可自动回滚
- **AND** SHALL 提供手动回滚说明（pg_dump + 重建表）

### Requirement: 压缩策略配置
系统 SHALL 为超表配置自动压缩策略，压缩超过指定天数的旧数据。

配置项：
- `TIMESCALE_COMPRESS_AFTER_DAYS`：压缩阈值（默认 30 天）
- `TIMESCALE_COMPRESS_SEGMENT_BY`：压缩分段字段（默认 `ts_code`）
- `TIMESCALE_COMPRESS_ORDER_BY`：压缩排序字段（默认 `trade_date DESC`）

#### Scenario: 启用压缩策略
- **WHEN** 超表迁移完成后
- **THEN** SHALL 对 stock_daily 和 technical_daily 启用压缩：`ALTER TABLE ... SET (timescaledb.compress, timescaledb.compress_segmentby = 'ts_code', timescaledb.compress_orderby = 'trade_date DESC')`
- **AND** SHALL 添加压缩策略：`SELECT add_compression_policy('stock_daily', interval '30 days')`

#### Scenario: 压缩效果
- **WHEN** 压缩策略执行后
- **THEN** 超过 30 天的 chunk SHALL 被自动压缩
- **AND** 压缩后的数据 SHALL 仍可正常查询（透明解压）
