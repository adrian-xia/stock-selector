## Context

当前日线同步实现（`app/scheduler/jobs.py:sync_daily_step()`）采用串行逐只股票同步策略，每只股票都要执行完整的 `login() → query() → logout()` 循环。Phase 5 验证发现，8000+ 只股票的完整同步预计需要 2-3 小时，严重影响盘后数据更新的时效性。

**当前架构：**
- `BaoStockClient` 每次调用 `fetch_daily()` 都会在 `_fetch_daily_sync()` 中执行 login/logout
- `sync_daily_step()` 串行遍历所有股票，逐只调用 `DataManager.sync_daily()`
- 无连接复用，无并发控制

**约束条件：**
- BaoStock API 是同步的，需要通过 `asyncio.to_thread()` 包装
- BaoStock 有 QPS 限制（当前通过 `Semaphore` 控制）
- 必须保持现有公共 API 接口不变，确保向后兼容
- 数据库写入已有批量优化（`batch_insert` 自动分片）

## Goals / Non-Goals

**Goals:**
- 实现 BaoStock 连接池，复用登录会话，减少 login/logout 开销
- 支持批量并发同步，将 8000+ 只股票的同步时间从 2-3 小时降低到 15-30 分钟
- 保持现有 API 接口不变，确保向后兼容
- 添加进度日志，提升可观测性
- 支持配置化的批量大小和并发数

**Non-Goals:**
- 不修改 BaoStock API 本身（它是第三方库）
- 不改变数据库 schema
- 不实现分布式同步（单机部署足够）
- 不支持实时数据流（仍然是批量盘后同步）

## Decisions

### Decision 1: 连接池设计 — 基于 asyncio.Queue 的简单池

**选择：** 使用 `asyncio.Queue` 实现连接池，而不是第三方库（如 `aiopool`）

**理由：**
- BaoStock 的 login/logout 是同步操作，需要在线程池中执行
- `asyncio.Queue` 足够简单，易于理解和维护
- 避免引入额外依赖

**实现要点：**
- 连接池维护一个 `asyncio.Queue[BaoStockSession]`
- `BaoStockSession` 封装 login 状态和最后使用时间
- `acquire()` 从队列获取连接，如果队列为空且未达到池大小上限，则创建新连接
- `release()` 将连接放回队列，检查会话是否过期（TTL）
- 支持 async context manager：`async with pool.acquire() as session:`

**替代方案：**
- 使用第三方连接池库 → 增加依赖，且需要适配 BaoStock 的同步 API
- 使用全局单例连接 → 无法支持并发，性能提升有限

### Decision 2: 批量同步策略 — 分批 + 并发控制

**选择：** 将股票列表分批（batch），每批内并发执行，批间串行

**理由：**
- 避免一次性创建 8000+ 个并发任务，导致资源耗尽
- 分批可以提供进度反馈（每批完成后记录日志）
- 批内并发可以充分利用连接池和网络带宽

**实现要点：**
- 默认批量大小：100 只股票/批
- 默认并发数：10 个任务
- 使用 `asyncio.Semaphore` 控制批内并发数
- 使用 `asyncio.gather()` 收集批内结果

**配置项：**
```python
DAILY_SYNC_BATCH_SIZE = 100  # 每批股票数
DAILY_SYNC_CONCURRENCY = 10  # 批内并发数
BAOSTOCK_POOL_SIZE = 5       # 连接池大小
```

**替代方案：**
- 全部串行 → 性能提升有限
- 全部并发 → 资源耗尽，难以控制
- 使用消息队列（Celery/RQ）→ 过度设计，单机部署不需要

### Decision 3: 向后兼容策略 — 可选连接池参数

**选择：** `BaoStockClient` 构造函数接受可选的 `connection_pool` 参数

**理由：**
- 现有代码（如单元测试、手动脚本）无需修改
- 新代码可以显式传入连接池以获得性能提升
- 渐进式迁移，降低风险

**实现要点：**
```python
class BaoStockClient:
    def __init__(self, connection_pool: BaoStockConnectionPool | None = None, ...):
        self._pool = connection_pool
        # 其他初始化...

    def _fetch_daily_sync(self, code, start_date, end_date):
        if self._pool:
            # 使用连接池
            session = self._pool.acquire_sync()  # 同步获取
            try:
                # 使用 session 查询
                ...
            finally:
                self._pool.release_sync(session)
        else:
            # 旧逻辑：login → query → logout
            self._login()
            try:
                ...
            finally:
                self._logout()
```

**替代方案：**
- 强制使用连接池 → 破坏向后兼容性
- 创建新的 `BaoStockClientV2` → 代码重复，维护成本高

### Decision 4: 连接池生命周期管理 — 全局单例 + 手动关闭

**选择：** 连接池作为全局单例，在应用启动时初始化，关闭时手动清理

**理由：**
- 连接池应该在整个应用生命周期内复用
- 避免每次调用都创建/销毁连接池
- FastAPI 的 lifespan 事件可以管理初始化和清理

**实现要点：**
```python
# app/data/pool.py
_pool: BaoStockConnectionPool | None = None

def get_pool() -> BaoStockConnectionPool:
    global _pool
    if _pool is None:
        _pool = BaoStockConnectionPool(size=settings.baostock_pool_size)
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化连接池
    get_pool()
    yield
    # 关闭时清理连接池
    await close_pool()
```

**替代方案：**
- 每次使用时创建连接池 → 失去复用优势
- 使用依赖注入 → 增加复杂度，收益不明显

### Decision 5: 错误处理 — 快速失败 vs 重试

**选择：** 瞬时错误（网络超时）重试 3 次，永久错误（无效股票代码）快速失败

**理由：**
- 网络抖动是常见的瞬时错误，重试可以提高成功率
- 永久错误重试无意义，浪费时间
- 单只股票失败不应阻断整体同步

**实现要点：**
- 在 `BaoStockClient._with_retry()` 中已有重试逻辑
- 区分 `DataSourceError`（永久错误）和其他异常（瞬时错误）
- 批量同步中捕获单只股票的异常，记录日志后继续

**替代方案：**
- 所有错误都重试 → 浪费时间
- 所有错误都快速失败 → 成功率低

## Risks / Trade-offs

### Risk 1: 连接池会话过期
**风险：** BaoStock 会话可能在空闲一段时间后过期，导致查询失败

**缓解措施：**
- 设置会话 TTL（默认 3600 秒），超时后自动重新 login
- 在 `acquire()` 时检查会话是否过期
- 查询失败时捕获异常，重新 login 后重试

### Risk 2: 并发过高触发限流
**风险：** 并发数过高可能触发 BaoStock 的限流机制

**缓解措施：**
- 默认并发数设置为 10（保守值）
- 通过配置项允许用户调整
- 保留现有的 QPS 限制（`Semaphore`）

### Risk 3: 连接池资源泄漏
**风险：** 如果 `release()` 未被调用，连接会永久占用

**缓解措施：**
- 强制使用 async context manager：`async with pool.acquire() as session:`
- 在 `__aexit__` 中确保 `release()` 被调用
- 添加连接池健康检查，定期清理僵尸连接

### Risk 4: 测试用例需要更新
**风险：** 现有测试用例可能依赖 login/logout 的调用次数

**缓解措施：**
- 测试用例默认不使用连接池（向后兼容）
- 新增专门的连接池测试用例
- 使用 mock 隔离 BaoStock API

### Trade-off 1: 内存占用 vs 性能
**权衡：** 连接池会占用额外内存（每个连接维护一个 BaoStock 会话）

**决策：** 接受内存开销，因为性能提升显著（4-8 倍）

### Trade-off 2: 代码复杂度 vs 可维护性
**权衡：** 连接池增加了代码复杂度

**决策：** 复杂度可控，且有清晰的抽象边界（`BaoStockConnectionPool` 独立模块）

## Migration Plan

### Phase 1: 实现连接池（不影响现有功能）
1. 新增 `app/data/pool.py`，实现 `BaoStockConnectionPool`
2. 修改 `BaoStockClient` 支持可选的 `connection_pool` 参数
3. 添加单元测试验证连接池功能
4. 在 `app/main.py` 中集成连接池生命周期管理

### Phase 2: 实现批量同步（可选功能）
1. 新增 `app/data/batch.py`，实现 `batch_sync_daily()`
2. 添加配置项：`DAILY_SYNC_BATCH_SIZE`, `DAILY_SYNC_CONCURRENCY`
3. 添加单元测试验证批量同步功能

### Phase 3: 集成到调度器（替换现有实现）
1. 修改 `app/scheduler/jobs.py:sync_daily_step()` 使用批量同步
2. 添加进度日志
3. 在测试环境验证性能提升

### Phase 4: 生产部署
1. 更新 `.env.example` 和文档
2. 在生产环境部署，监控性能指标
3. 根据实际情况调整配置参数

### Rollback Strategy
如果批量同步出现问题，可以快速回退：
1. 修改 `sync_daily_step()` 恢复旧逻辑（逐只串行）
2. 重启服务
3. 连接池代码保留（不影响旧逻辑）

## Open Questions

1. **BaoStock 会话的实际 TTL 是多少？**
   - 需要实际测试确定
   - 当前设置为 3600 秒（1 小时），可能需要调整

2. **最优的批量大小和并发数是多少？**
   - 需要在生产环境实测
   - 当前设置为保守值（batch=100, concurrency=10）

3. **是否需要支持断点续传？**
   - 如果同步中断，是否需要记录进度，下次从断点继续？
   - V1 暂不支持，如果需要可以在 V2 实现
