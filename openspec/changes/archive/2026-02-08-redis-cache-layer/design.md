## Context

当前策略引擎 Pipeline 每次执行都直接查询 PostgreSQL `technical_daily` 表。技术指标每日收盘后批量计算一次，属于典型的高频读、低频写场景。项目已在 `app/config.py` 中预留了 Redis 连接配置（host/port/db/password），但尚未实际使用。

设计文档 `11-系统设计-缓存策略.md` 定义了完整的缓存方案，V1 简化为：只缓存技术指标和选股结果，不做分布式锁、JWT 黑名单等 V2 场景。

## Goals / Non-Goals

**Goals:**
- 实现 Redis 异步连接池，在 FastAPI lifespan 中管理生命周期
- 实现技术指标 Cache-Aside 读取（单只 + 批量 Pipeline 优化）
- 实现选股结果缓存（Pipeline 执行后写入，按日期读取）
- 实现定时全量刷新（盘后链路新增缓存刷新步骤）
- 实现应用启动时缓存预热
- Redis 不可用时静默降级，直接回源 DB

**Non-Goals:**
- 不做分布式锁（V2，单机无需）
- 不做实时行情缓存（V2，V1 只做盘后批处理）
- 不做 WebSocket 订阅者管理（V2）
- 不做缓存监控 API（V2）
- 不修改 Pipeline 内部的数据查询逻辑——缓存层是独立的读加速层

## Decisions

### D1: Redis 客户端 — 使用 `redis[hiredis]`

使用 `redis` 包（原 `redis-py`）的异步接口 `redis.asyncio`，搭配 `hiredis` C 解析器加速。

**理由：**
- `redis` 是 Python 生态最成熟的 Redis 客户端，原生支持 async
- `hiredis` 提供 C 级别的协议解析，批量操作性能提升 ~10x
- 项目 `app/config.py` 已预留 `redis_host`/`redis_port` 等配置

**替代方案：**
- `aioredis`：已合并入 `redis` 包，不再独立维护
- `coredis`：社区较小，文档不如 `redis` 完善

### D2: 连接管理 — FastAPI lifespan + 模块级单例

在 `app/cache/redis_client.py` 中提供 `init_redis()` / `close_redis()` / `get_redis()` 三个函数。`init_redis()` 在 FastAPI lifespan 启动时调用，`get_redis()` 返回已初始化的连接实例。

**理由：**
- 与现有 `app/database.py` 的模式一致（模块级 engine + session_factory）
- 避免在每个请求中创建/销毁连接
- Redis 不可用时 `get_redis()` 返回 `None`，调用方据此降级

**替代方案：**
- FastAPI Depends 注入：增加每个端点的参数复杂度，且定时任务无法使用 Depends

### D3: 缓存 Key 设计 — 遵循设计文档

严格遵循 `11-系统设计-缓存策略.md` 的 Key 设计：
- `tech:{ts_code}:latest` — Hash，存储最新技术指标
- `pipeline:result:{date}` — String(JSON)，存储选股结果

**理由：**
- 设计文档已充分考虑了内存估算（~5-10MB）和 TTL 策略
- Hash 结构支持按字段读取，适合技术指标的部分查询场景

### D4: 降级策略 — Redis 不可用时静默回源

所有缓存读写操作都 try/except 包裹 Redis 异常。Redis 不可用时：
- 读取：直接回源 DB，功能不受影响
- 写入：跳过缓存写入，记录 warning 日志
- 预热：跳过预热，记录 warning 日志

**理由：**
- 缓存是加速层，不是数据源，不应阻断核心流程
- 与 AI 模块的降级策略保持一致

### D5: 缓存刷新时机 — 盘后链路第 4 步

在 `run_post_market_chain` 中，技术指标计算完成后、策略管道执行前，插入缓存刷新步骤。顺序变为：日线同步 → 技术指标 → **缓存刷新** → 策略管道。

**理由：**
- 策略管道可以直接从缓存读取刚刷新的指标，减少 DB 压力
- 刷新失败不阻断链路（策略管道会 Cache Miss 回源 DB）

### D6: 技术指标字段映射 — 对齐 technical_daily 表

缓存的 Hash 字段名与 `technical_daily` 表列名保持一致（`ma5`、`macd_dif`、`rsi6` 等），不做重命名。

**理由：**
- 减少映射层，代码更简单
- 设计文档中的字段名（`dif`/`dea`/`k`/`d`）与实际表结构不同，以实际表结构为准

## Risks / Trade-offs

| 风险 | 缓解措施 |
|:---|:---|
| Redis 服务未启动导致应用启动失败 | `init_redis()` 捕获连接异常，降级为无缓存模式，应用正常启动 |
| 缓存数据过期但未刷新（定时任务失败） | TTL 25 小时覆盖到次日刷新；最坏情况 Cache Miss 回源 DB |
| 全量刷新 5000+ 只股票耗时 | Pipeline 批量写入（每 500 条一批），预计 < 5 秒 |
| 选股结果缓存与实际不一致 | 每次 Pipeline 执行都覆盖写入，TTL 48 小时自动过期 |
