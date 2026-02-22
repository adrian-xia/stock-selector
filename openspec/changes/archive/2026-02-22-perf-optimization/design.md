## Context

当前系统使用 SQLAlchemy `pg_insert().values()` 进行批量 UPSERT，每批最多 5000 行（受 asyncpg 32767 参数限制动态调整）。90+ 张 raw 表和业务表的数据量持续增长，stock_daily 已超 150 万行。写入路径为：API → raw 表（ON CONFLICT DO UPDATE）→ ETL → 业务表（ON CONFLICT DO NOTHING）。

连接池配置为 pool_size=5, max_overflow=10，ETL 批量大小 5000。Redis 缓存层已就绪（Cache-Aside 模式）。

## Goals / Non-Goals

**Goals:**
- 写入性能提升：COPY 协议替代 INSERT，目标 10 倍提升
- 全量导入加速：索引管理（删除→导入→重建），目标 3-5 倍提升
- 存储优化：TimescaleDB 超表 + 压缩，目标节省 90% 空间
- 查询优化：补充 raw 表复合索引，优化 ETL 查询路径
- 连接池调优：匹配实际并发需求

**Non-Goals:**
- 不做读写分离或主从复制
- 不做分布式数据库迁移
- 不做应用层分片
- 不修改 Redis 缓存策略（已在 V1 完成）
- 不做分钟线数据优化（stock_min 表 V1 未使用）

## Decisions

### D1: COPY 协议写入方案

**选择：** 临时表 + COPY + UPSERT 三步法

**方案：**
1. 创建与目标表同结构的临时表（TEMPORARY TABLE，会话结束自动清理）
2. 使用 asyncpg `copy_records_to_table()` 将数据 COPY 到临时表
3. 从临时表 INSERT INTO 目标表 ON CONFLICT DO UPDATE/NOTHING

**理由：** PostgreSQL COPY 不支持 ON CONFLICT，但我们的写入场景需要幂等性（断点续传、重复同步）。临时表方案兼顾 COPY 的高性能和 UPSERT 的幂等性。

**替代方案：**
- 直接 COPY（无冲突处理）：不适用，数据可能重复
- COPY + DELETE 再 INSERT：有数据丢失风险，事务隔离复杂
- 保持现有 INSERT：性能不够

**实现要点：**
- 通过 `engine.raw_connection()` 获取底层 asyncpg 连接
- 临时表命名：`_tmp_{table_name}`，ON COMMIT DROP
- 批量大小：单次 COPY 最大 50000 行（内存可控）
- Fallback：COPY 失败时自动降级到现有 batch_insert

### D2: 索引管理策略

**选择：** 仅在全量导入（init_data / backfill）时启用索引管理，日常增量同步不动索引

**理由：** 日常同步每日约 5000 行，索引维护开销可忽略。全量导入可能涉及数百万行，索引删除重建收益显著。

**实现：**
- 提供 `drop_indexes(table)` 和 `rebuild_indexes(table)` 工具函数
- 仅删除非主键索引（主键约束保留）
- 在 batch.py 的全量导入流程中包裹：drop → import → rebuild
- 记录索引操作日志，rebuild 失败时告警

### D3: TimescaleDB 超表迁移

**选择：** stock_daily 和 technical_daily 两张核心大表迁移为超表，其他表保持普通表

**理由：** 这两张表数据量最大（各 150 万+ 行，每日增长 5000 行），时序查询模式明显（按日期范围查询）。raw 表虽多但单表数据量较小，迁移收益不大。

**实现：**
- Alembic 迁移脚本：`CREATE EXTENSION IF NOT EXISTS timescaledb` → `create_hypertable()`
- 分区维度：trade_date，chunk 间隔 1 个月
- 压缩策略：超过 30 天的 chunk 自动压缩，segment_by ts_code，order_by trade_date DESC
- 数据保留：不设自动删除策略（投资数据需要长期保留）
- **兼容性：** TimescaleDB 为可选依赖，未安装时跳过超表迁移，使用普通表 + 手动分区

### D4: 查询优化

**选择：** 为高频查询路径补充复合索引

**新增索引：**
- raw 表：`(ts_code, trade_date)` 复合索引（ETL 阶段按 ts_code + trade_date 查询）
- stock_daily：`(trade_date, ts_code)` 索引（策略管道按日期查全市场）

**理由：** 当前 raw 表仅有 trade_date 单列索引，ETL 阶段的 JOIN 查询需要 ts_code 参与，缺少复合索引导致全表扫描。

### D5: 连接池调优

**选择：** pool_size 从 5 调整为 10，max_overflow 从 10 调整为 20

**理由：** 盘后链路并发执行多个同步任务（P0-P5 + ETL + 指标计算 + AI 分析），当前 15 个连接上限可能不足。调整为 30 个连接上限，匹配实际并发需求。

## Risks / Trade-offs

- **TimescaleDB 依赖** → 设为可选扩展，未安装时降级为普通表。Alembic 迁移脚本检测扩展是否可用。
- **COPY 临时表内存** → 限制单次 COPY 批量为 50000 行，超过则分批。
- **超表迁移不可逆** → 迁移前自动备份表数据（pg_dump），提供回滚脚本。
- **索引重建耗时** → 使用 `CREATE INDEX CONCURRENTLY` 避免锁表，重建失败时保留日志并告警。
- **asyncpg raw connection 生命周期** → 确保 COPY 操作在 try/finally 中释放连接，避免连接泄漏。

## Migration Plan

1. **Phase 1 — COPY 写入层**：实现 copy_protocol_writer，集成到 etl.py，保留 fallback
2. **Phase 2 — 索引管理**：实现 index_management 工具，集成到全量导入流程
3. **Phase 3 — TimescaleDB**：Alembic 迁移脚本，超表转换 + 压缩策略
4. **Phase 4 — 查询优化**：新增索引 + 连接池调优

**回滚策略：** 每个 Phase 独立，可单独回滚。COPY 写入有 fallback 到 INSERT；TimescaleDB 迁移前有备份。

## Open Questions

- TimescaleDB 社区版是否满足需求，还是需要企业版的高级压缩功能？（初步判断社区版足够）
- raw 表是否也值得迁移为超表？（当前判断不需要，单表数据量不大）
