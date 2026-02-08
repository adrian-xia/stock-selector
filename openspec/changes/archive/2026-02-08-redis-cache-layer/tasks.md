## 1. 依赖与配置

- [x] 1.1 在 `pyproject.toml` 中添加 `redis[hiredis]` 依赖并执行 `uv sync`
- [x] 1.2 在 `app/config.py` 的 `Settings` 类中添加缓存配置项：`cache_tech_ttl`、`cache_pipeline_result_ttl`、`cache_warmup_on_startup`、`cache_refresh_batch_size`
- [x] 1.3 在 `.env.example` 中添加 `# --- Cache (Redis) ---` 配置段

## 2. Redis 连接管理

- [x] 2.1 创建 `app/cache/__init__.py`
- [x] 2.2 创建 `app/cache/redis_client.py`，实现 `init_redis()`、`get_redis()`、`close_redis()` 三个函数，使用模块级单例模式
- [x] 2.3 在 `app/main.py` 的 lifespan 中集成 `init_redis()` 和 `close_redis()` 调用

## 3. 技术指标缓存

- [x] 3.1 创建 `app/cache/tech_cache.py`，实现 `TechIndicatorCache` 类，包含 `get_latest()` 和 `get_batch()` 方法（Cache-Aside 模式，字段名对齐 `technical_daily` 表）
- [x] 3.2 在 `TechIndicatorCache` 中实现 Redis 异常捕获与静默降级逻辑
- [x] 3.3 实现 `refresh_all_tech_cache()` 全量刷新函数，使用 Pipeline 分批写入
- [x] 3.4 实现 `warmup_cache()` 预热函数，检查已有数据量后决定是否全量刷新
- [x] 3.5 在 `app/main.py` 的 lifespan 中集成缓存预热调用（受 `CACHE_WARMUP_ON_STARTUP` 控制）

## 4. 选股结果缓存

- [x] 4.1 创建 `app/cache/pipeline_cache.py`，实现 `cache_pipeline_result()` 和 `get_pipeline_result()` 函数，包含 Redis 异常降级

## 5. 定时任务集成

- [x] 5.1 在 `app/scheduler/jobs.py` 中添加 `cache_refresh_step()` 函数
- [x] 5.2 修改 `run_post_market_chain()` 在技术指标计算后、策略管道前插入缓存刷新步骤（失败不阻断链路）

## 6. 单元测试

- [x] 6.1 编写 `tests/unit/test_redis_client.py`：测试 init/get/close 生命周期及 Redis 不可用降级
- [x] 6.2 编写 `tests/unit/test_tech_cache.py`：测试 get_latest 缓存命中/未命中、get_batch Pipeline、refresh_all 全量刷新、warmup 预热逻辑
- [x] 6.3 编写 `tests/unit/test_pipeline_cache.py`：测试选股结果缓存读写及降级
- [x] 6.4 编写 `tests/unit/test_cache_refresh_step.py`：测试盘后链路缓存刷新步骤及失败降级
