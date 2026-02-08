## Why

策略引擎 Pipeline 每次执行都直接查询 PostgreSQL 的 `technical_daily` 表获取技术指标，5000+ 只股票的全表扫描对数据库造成不必要的压力。技术指标每日收盘后才更新一次，属于高频读取、低频变更的数据，非常适合用 Redis 做读加速缓存。

## What Changes

- 新增 Redis 连接管理：基于 `redis.asyncio` 的异步连接池，在 FastAPI lifespan 中初始化和关闭
- 新增技术指标缓存层（`TechIndicatorCache`）：Cache-Aside 模式，先查 Redis Hash，Miss 则回源 DB 并回填
- 新增选股结果缓存：Pipeline 执行完成后将结果缓存为 JSON，前端 API 可直接读取
- 新增缓存全量刷新函数：定时任务在盘后调用，批量写入所有股票的最新技术指标
- 新增缓存预热：应用启动时检查 Redis 是否有数据，无则全量刷新
- 新增缓存相关配置项（TTL、批次大小、是否预热等）

## Capabilities

### New Capabilities
- `redis-connection`: Redis 异步连接池管理，lifespan 集成，连接获取函数
- `tech-indicator-cache`: 技术指标缓存层，支持单只/批量读取（Pipeline 优化）、Cache Miss 回源、全量刷新、启动预热
- `pipeline-result-cache`: 选股结果缓存，Pipeline 执行后写入、按日期读取

### Modified Capabilities
- `app-config`: 新增 Redis 缓存相关配置项（TTL、批次大小、预热开关）
- `scheduler-jobs`: 盘后链路新增缓存刷新步骤

## Impact

- **新增代码：** `app/cache/` 目录（redis_client.py、tech_cache.py、pipeline_cache.py）
- **修改代码：** `app/main.py`（lifespan 集成 Redis）、`app/config.py`（新增配置）、`app/scheduler/jobs.py`（新增刷新步骤）
- **依赖新增：** `redis[hiredis]`（异步 Redis 客户端 + C 加速解析器）
- **配置新增：** `.env` 中增加 `CACHE_TECH_TTL`、`CACHE_PIPELINE_RESULT_TTL`、`CACHE_WARMUP_ON_STARTUP`、`CACHE_REFRESH_BATCH_SIZE` 等
- **基础设施：** 需要本地运行 Redis 服务（默认 localhost:6379）
