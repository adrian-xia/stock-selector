## 1. COPY 协议写入层

- [x] 1.1 实现 `get_raw_connection()` 异步上下文管理器（app/database.py），从 async engine 获取底层 asyncpg 连接
- [x] 1.2 实现 `copy_insert()` 函数（app/data/copy_writer.py），临时表 + COPY + UPSERT 三步法，支持 conflict="update" 和 conflict="nothing" 两种模式
- [x] 1.3 实现大批量自动分批（超过 50000 行时分批 COPY）
- [x] 1.4 实现 COPY 失败自动降级到 batch_insert / _upsert_raw，记录 WARNING 日志
- [x] 1.5 实现 COPY 写入性能日志（表名、行数、耗时、写入速率）
- [x] 1.6 为 copy_insert 编写单元测试

## 2. ETL 层集成 COPY 协议

- [x] 2.1 修改 `batch_insert()` 函数（app/data/etl.py），新增 use_copy 参数，默认优先使用 COPY 协议写入
- [x] 2.2 修改 `_upsert_raw()` 方法（app/data/manager.py），优先使用 copy_insert(conflict="update")
- [x] 2.3 验证 sync_raw_daily / etl_daily 流程使用 COPY 协议正常工作
- [x] 2.4 验证资金流向、指数、板块、P5 数据同步使用 COPY 协议正常工作

## 3. 索引管理

- [x] 3.1 实现 `drop_indexes(engine, table_name)` 函数（app/data/index_mgmt.py），删除非主键索引并返回索引定义
- [x] 3.2 实现 `rebuild_indexes(engine, index_definitions)` 函数，使用 CREATE INDEX CONCURRENTLY 重建索引
- [x] 3.3 实现 `with_index_management(engine, table_names)` 异步上下文管理器
- [x] 3.4 修改 batch_sync_daily（app/data/batch.py），新增 full_import 参数，全量导入时集成索引管理
- [x] 3.5 为索引管理编写单元测试

## 4. TimescaleDB 超表迁移

- [x] 4.1 实现 `is_timescaledb_available(engine)` 检测函数
- [x] 4.2 新增配置项 TIMESCALE_ENABLED、TIMESCALE_COMPRESS_AFTER_DAYS（app/config.py + .env.example）
- [x] 4.3 创建 Alembic 迁移脚本：CREATE EXTENSION timescaledb + stock_daily/technical_daily 转超表（条件执行）
- [x] 4.4 在迁移脚本中配置压缩策略（compress_segmentby=ts_code, compress_orderby=trade_date DESC, 30天自动压缩）
- [x] 4.5 验证 TimescaleDB 不可用时迁移脚本安全跳过

## 5. 查询优化与连接池调优

- [x] 5.1 创建 Alembic 迁移脚本：为 P0-P5 raw 表补充 (ts_code, trade_date) 复合索引
- [x] 5.2 调整连接池默认值：pool_size 从 5 改为 10，max_overflow 从 10 改为 20（app/config.py）
- [x] 5.3 验证 ETL 查询使用新索引（EXPLAIN ANALYZE）

## 6. 文档与配置更新

- [x] 6.1 更新 .env.example 新增 TIMESCALE_ENABLED、TIMESCALE_COMPRESS_AFTER_DAYS 配置项
- [x] 6.2 更新 docs/design/99-实施范围-V1与V2划分.md 标记性能优化为已实施
- [x] 6.3 更新 README.md 说明性能优化功能和 TimescaleDB 可选依赖
- [x] 6.4 更新 CLAUDE.md 同步技术栈和 V1 范围变更
- [x] 6.5 更新 PROJECT_TASKS.md 标记 Change 13 已完成
