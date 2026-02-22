## Why

当前数据写入使用 SQLAlchemy `pg_insert().values()` 批量 UPSERT，每批 5000 行通过参数化 INSERT 语句逐批提交。随着 90+ 张 raw 表和业务表的数据量增长（stock_daily 已超 150 万行），写入性能成为瓶颈。PostgreSQL COPY 协议可提升写入速度约 10 倍，索引管理策略可在全量导入时再提升 3-5 倍，TimescaleDB 超表可实现自动分区和数据压缩（节省约 90% 存储空间）。

## What Changes

- 引入 PostgreSQL COPY 协议写入：使用 asyncpg 的 `copy_records_to_table()` 替代当前 `pg_insert().values()` 批量 INSERT，适用于大批量数据写入场景（raw 表同步、ETL 批量插入）
- 全量导入索引管理：全量导入前自动删除非主键索引，导入完成后重建，减少写入时的索引维护开销
- TimescaleDB 超表迁移：将 `stock_daily` 等大型时序表转为 Hypertable，启用自动分区（按月）和原生压缩策略，配置数据保留策略
- 查询优化：为 raw 表补充复合索引 `(ts_code, trade_date)`，优化 ETL 阶段的查询性能；分析并优化慢查询
- 连接池调优：根据并发场景优化 `pool_size` 和 `max_overflow` 参数

## Capabilities

### New Capabilities
- `copy-protocol-writer`: PostgreSQL COPY 协议批量写入能力，封装 asyncpg copy_records_to_table，支持冲突处理（先写临时表再 UPSERT）
- `index-management`: 全量导入时的索引生命周期管理（删除、重建、状态跟踪）
- `timescaledb-hypertable`: TimescaleDB 超表迁移、压缩策略配置、数据保留策略

### Modified Capabilities
- `etl-pipeline`: 写入路径从 batch_insert 切换到 COPY 协议，保留 fallback 到原有 INSERT 方式
- `database-schema`: 新增 TimescaleDB 扩展依赖，stock_daily 等表转为超表
- `database-connection`: 连接池参数调优，支持 COPY 协议所需的 raw connection 获取
- `batch-daily-sync`: 全量导入场景集成索引管理（删除→导入→重建）
- `data-manager`: sync_raw_daily 和 etl_daily 切换到 COPY 协议写入

## Impact

- **数据库：** 需安装 TimescaleDB 扩展（`CREATE EXTENSION IF NOT EXISTS timescaledb`），stock_daily 等表迁移为超表（不可逆操作，需备份）
- **依赖：** 无新 Python 依赖，asyncpg 已内置 COPY 支持
- **代码：** 主要修改 `app/data/etl.py`（写入层）、`app/data/manager.py`（调用层）、`app/database.py`（连接池）
- **迁移：** 需要 Alembic 迁移脚本处理 TimescaleDB 超表转换和新索引
- **配置：** 新增 TimescaleDB 相关配置项（压缩策略、保留天数）
- **兼容性：** COPY 写入保留 fallback 到 INSERT 方式，TimescaleDB 为可选依赖（不安装则使用普通表 + 分区）
