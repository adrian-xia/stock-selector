## Context

当前系统的数据完整性检查存在以下根本缺陷：

**现状问题**：
- `detect_missing_dates` 只检查交易日是否有任何数据（`SELECT DISTINCT trade_date`），不检查该日期是否有所有应该有的股票数据
- 启动时不更新股票列表，使用数据库中的旧数据（依赖周六定时任务更新）
- 每日增量同步只同步当天数据，不补齐新上市股票的历史数据
- 批量同步失败的股票不会重试，累积成大量缺失数据
- 不考虑股票的上市和退市日期，浪费 API 调用
- **进度追踪基于"每日重置"模型，无法实现真正的断点续传**
- **生产和测试环境共用同一数据库和 Redis，存在数据污染风险**

**核心变化**：
1. 生产/测试环境物理隔离（不同数据库 + Redis db）
2. 进度追踪表改为累积模型（data_date + indicator_date，非每日重置）
3. 数据拉取和指标计算都按批次处理，每批更新进度
4. 启动时从进度表恢复，实现真正的断点续传

**约束**：
- 不能显著增加启动时间（目标：< 5 分钟）
- 不能影响每日盘后链路的执行时间（目标：增加 < 1 分钟）
- 必须考虑 BaoStock API 限流（QPS 限制）

## Goals / Non-Goals

**Goals:**
1. 环境隔离：生产和测试使用不同数据库和 Redis db，互不干扰
2. 累积进度模型：每只股票追踪 data_date 和 indicator_date，支持断点续传
3. 批量处理：数据拉取和指标计算按 365 天/批处理，每批更新进度
4. 启动时自动更新股票列表，确保使用最新的股票基本信息
5. 精确检测数据完整性，发现并补齐缺失的股票数据
6. 智能过滤不应该有数据的股票（未上市、已退市）
7. 失败股票自动重试，降低数据缺失率

**Non-Goals:**
1. 不处理分钟级数据的完整性检查（只处理日线数据）
2. 不实现实时监控和告警（V2 功能）
3. 不优化 BaoStock API 调用性能（使用现有连接池机制）

## Decisions

### 决策 1：启动时更新股票列表的时机

**选择**：在数据完整性检查之前更新股票列表

**理由**：
- 确保完整性检查使用最新的股票列表
- 新上市的股票会被立即发现并补齐
- 退市的股票状态会及时更新，避免浪费 API 调用

**实现**：
```python
async def start_scheduler(skip_integrity_check: bool = False) -> None:
    # 步骤 0：更新股票列表
    await sync_stock_list_on_startup()
    # 步骤 1：初始化进度表 + 从进度恢复同步
    await sync_from_progress(skip_check=skip_integrity_check)
    # 步骤 2：启动调度器
    _scheduler = create_scheduler()
    register_jobs(_scheduler)
    _scheduler.start()
```

---

### 决策 2：累积进度模型（替代每日重置模型）

**选择**：`stock_sync_progress` 表使用累积模型，记录每只股票的 `data_date` 和 `indicator_date`，表示数据/指标已同步到哪一天

**理由**：
- 每日重置模型无法实现断点续传：进程中断后，重启时不知道哪些股票已处理
- 累积模型天然支持断点续传：查询 `data_date < target_date` 即可找到待处理股票
- 新股自动从 `data_start_date` 开始（`data_date` 默认 `1900-01-01`）

**表设计**：
```sql
CREATE TABLE stock_sync_progress (
    ts_code VARCHAR(16) PRIMARY KEY,
    data_date DATE NOT NULL DEFAULT '1900-01-01',
    indicator_date DATE NOT NULL DEFAULT '1900-01-01',
    status VARCHAR(16) NOT NULL DEFAULT 'idle',  -- idle/syncing/computing/failed/delisted
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**字段说明**：
- `data_date`：日线数据已同步到的日期。`1900-01-01` 表示从未同步过
- `indicator_date`：技术指标已计算到的日期。`1900-01-01` 表示从未计算过
- `status`：当前状态
  - `idle`：空闲，等待处理
  - `syncing`：正在拉取数据
  - `computing`：正在计算指标
  - `failed`：处理失败（由 retry job 单独处理，主流程不再选取）
  - `delisted`：已退市，不再参与同步和完成率计算
- `retry_count`：累计重试次数，超过 `batch_sync_max_retries` 后停止自动重试
- `error_message`：最后一次错误信息

**退市状态的作用**：
- 筛选待同步股票时直接 `WHERE status NOT IN ('delisted')` ，无需 JOIN stocks 表
- 完成率计算时排除 delisted：`WHERE status != 'delisted'`
- 发现退市时通过事务同时更新 stocks 表和 progress 表，保证一致性

**与旧设计的对比**：
| 维度 | 旧设计（每日重置） | 新设计（累积模型） |
|------|-------------------|-------------------|
| 进度追踪 | synced_date + data_status/indicator_status | data_date + indicator_date |
| 每日操作 | 重置所有记录为 pending | 查询 data_date < today |
| 断点续传 | ❌ 重启后丢失进度 | ✅ 从 data_date 恢复 |
| 新股处理 | 需要特殊逻辑 | data_date=1900-01-01 自动触发 |
| 历史补齐 | 需要单独的补齐逻辑 | 统一流程，按批次追赶 |

---

### 决策 3：核心流程——基于进度表的同步

**选择**：启动和盘后链路共用同一套基于进度表的同步流程

**核心流程**：
```
启动/盘后链路：
0. acquire_sync_lock() — Redis/文件锁，防止并发执行
1. reset_stale_status() — 将 syncing/computing 重置为 idle（进程崩溃恢复）
2. init_sync_progress() — INSERT ... ON CONFLICT DO NOTHING（新股自动加入）
3. sync_delisted_status() — 同步退市状态（含反向恢复）
4. 查询 data_date < target_date 且 status NOT IN ('delisted', 'failed') 的股票
5. 对每只股票：
   a. start = data_start_date if data_date==1900-01-01 else data_date+1
   b. 按 365 天分批调用 sync_daily(code, batch_start, batch_end)
   c. 每批完成后 UPDATE data_date = batch_end
   d. 数据拉取完成后，按 365 天分批计算指标（加载 batch_start-LOOKBACK_DAYS 到 batch_end 的数据）
   e. 每批完成后 UPDATE indicator_date = batch_end
6. 检查完成率 → 策略执行/跳过
7. release_sync_lock()
```

**reset_stale_status() 实现**（进程崩溃恢复）：
```sql
-- 进程重启时，将卡在处理中的状态重置为 idle
UPDATE stock_sync_progress SET status = 'idle', updated_at = NOW()
WHERE status IN ('syncing', 'computing');
```

**init_sync_progress() 实现**：
```sql
-- 只插入不存在的股票，已有记录保持不变（保留进度）
INSERT INTO stock_sync_progress (ts_code, data_date, indicator_date, status)
SELECT ts_code, '1900-01-01', '1900-01-01', 'idle'
FROM stocks WHERE delist_date IS NULL
ON CONFLICT (ts_code) DO NOTHING;
```

**查询待同步股票**：
```sql
-- 排除 delisted 和 failed（failed 由 retry job 单独处理）
SELECT ts_code, data_date, indicator_date
FROM stock_sync_progress
WHERE status NOT IN ('delisted', 'failed')
  AND data_date < :target_date;
```

**断点续传示例**：
```
场景：同步 8000 只股票，处理到第 3000 只时进程崩溃
- 前 3000 只：data_date 已更新到 target_date
- 后 5000 只：data_date 仍然 < target_date
- 重启后：查询 data_date < target_date → 只处理剩余 5000 只
```

---

### 决策 4：失败重试机制（进度表驱动）

**选择**：失败的股票标记 status='failed'，定时任务重试，超过最大重试次数后停止

**理由**：
- 进度表已记录每只股票的状态，无需额外的失败记录表
- 重试时从 data_date 恢复，不会重复处理已完成的批次
- 定时任务（每天 20:00）在盘后链路完成后重试，当晚即可补跑策略
- 超过最大重试次数的股票不再自动重试，避免永久循环

**实现**：
```python
async def retry_failed_stocks_job():
    """重试 status='failed' 且 retry_count < max_retries 的股票。"""
    failed = await get_failed_stocks(max_retries=settings.batch_sync_max_retries)
    for stock in failed:
        stock.retry_count += 1
        try:
            await process_single_stock(stock)  # 从 data_date 恢复
        except Exception:
            if stock.retry_count >= settings.batch_sync_max_retries:
                logger.warning("股票 %s 达到最大重试次数 %d，停止自动重试",
                               stock.ts_code, settings.batch_sync_max_retries)
    # 重试后检查完整性 → 补跑策略
```

---

### 决策 5：智能过滤股票

**选择**：基于 `stock_sync_progress.status` 字段直接筛选，退市股票标记为 `delisted` 后不再参与任何同步流程

**理由**：
- 直接按 status 筛选，无需 JOIN stocks 表，查询更简单高效
- 退市状态持久化在进度表中，一次标记永久生效
- 发现退市时通过事务同时更新 stocks 和 progress，保证数据一致性

**筛选规则**：
```python
# 查询待同步股票：排除 delisted 和 failed（failed 由 retry job 处理）
async def get_stocks_needing_sync(target_date: date) -> list:
    # SELECT * FROM stock_sync_progress
    # WHERE status NOT IN ('delisted', 'failed')
    #   AND data_date < :target_date
    pass

# 完成率计算：排除 delisted
async def get_sync_summary(target_date: date) -> dict:
    # SELECT
    #   COUNT(*) FILTER (WHERE status != 'delisted') as total,
    #   COUNT(*) FILTER (WHERE status != 'delisted' AND data_date >= :target AND indicator_date >= :target) as done,
    #   COUNT(*) FILTER (WHERE status = 'failed') as failed
    # FROM stock_sync_progress
    pass
```

**退市检测时机**：
- `init_sync_progress()` 时：对比 stocks 表的 delist_date，新退市的股票在事务中标记 `delisted`
- 更新股票列表后：发现新退市股票时，事务更新 stocks + progress

---

### 决策 6：配置项设计

**新增配置项**：
```python
class Settings(BaseSettings):
    # --- 环境隔离 ---
    # env_file 通过 APP_ENV_FILE 环境变量指定，默认 .env
    # 测试时设置 APP_ENV_FILE=.env.test 使用测试数据库

    # --- 数据同步 ---
    data_start_date: str = "2024-01-01"           # 新股历史数据起始日期
    sync_stock_list_on_startup: bool = True        # 启动时是否更新股票列表
    batch_sync_max_retries: int = 2                # 批量同步最大重试次数
    data_completeness_threshold: float = 0.95      # 数据完整性阈值（95%）
    sync_batch_days: int = 365                     # 每批处理的天数
    sync_batch_timeout: int = 14400                  # 批量处理超时（秒），默认 4 小时

    # --- 定时重试 ---
    sync_failure_retry_cron: str = "0 20 * * *"    # 失败重试 cron（每天 20:00，盘后链路完成后）

    # --- 完整性告警 ---
    pipeline_completeness_deadline: str = "18:00"  # 完整性截止时间
```

---

### 决策 7：日期范围查询（保留）

**选择**：使用 BaoStock 日期范围查询一次性获取历史数据

**理由**：
- `query_history_k_data_plus` 原生支持日期范围，1 次 API 调用获取一只股票的全部历史数据
- 比逐日调用减少 97% 的 API 调用量

---

### 决策 8：完整性检查——基于进度表

**选择**：完整性检查改为查询进度表，而非逐交易日统计

**理由**：
- 进度表已记录每只股票的 data_date，直接查 `data_date < target_date` 即可
- 无需复杂的 GROUP BY 查询
- 完成率 = `COUNT(data_date >= target_date AND indicator_date >= target_date) / COUNT(*)`

**实现**：
```python
async def get_sync_summary(target_date: date) -> dict:
    """查询同步进度摘要（排除 delisted 股票）。"""
    # SELECT
    #   COUNT(*) FILTER (WHERE status != 'delisted') as total,
    #   COUNT(*) FILTER (WHERE status != 'delisted' AND data_date >= :target) as data_done,
    #   COUNT(*) FILTER (WHERE status != 'delisted' AND indicator_date >= :target) as indicator_done,
    #   COUNT(*) FILTER (WHERE status = 'failed') as failed
    # FROM stock_sync_progress
    pass
```

---

### 决策 9：环境隔离

**选择**：通过 `APP_ENV_FILE` 环境变量指定 `.env` 文件路径，实现物理隔离

**方案**：
- 生产环境：`APP_ENV_FILE=.env.prod`（或默认 `.env`），使用 `stock_selector` 数据库 + Redis db 0
- 测试环境：`APP_ENV_FILE=.env.test`，使用 `stock_selector_test` 数据库 + Redis db 1
- 开发环境：默认 `.env`，使用 `stock_selector` 数据库 + Redis db 0

**config.py 改造**：
```python
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get(
            "APP_ENV_FILE",
            str(Path(__file__).resolve().parent.parent / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

**alembic/env.py 改造**：
```python
# 从 Settings 读取数据库 URL，而非 alembic.ini
from app.config import settings
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))
```

---

### 决策 10：批量数据处理

**选择**：按 365 天/批拉取数据，每批完成后更新 `data_date`

**理由**：
- 365 天/批平衡了 API 调用次数和单次数据量
- 每批更新进度，中断后可从断点恢复
- 新股从 `data_start_date` 开始，老股从 `data_date+1` 开始

**实现**：
```python
async def sync_stock_data_in_batches(
    code: str, start_date: date, end_date: date, batch_days: int = 365
) -> None:
    """按批次拉取数据，每批在事务中完成写入 + 更新进度。"""
    current = start_date
    while current <= end_date:
        batch_end = min(current + timedelta(days=batch_days - 1), end_date)
        rows = await fetch_daily_from_api(code, current, batch_end)
        # 事务：批量写入日线数据 + 更新 data_date，保证原子性
        async with session.begin():
            await bulk_insert_daily(session, rows)
            await update_data_progress(session, code, batch_end)
        current = batch_end + timedelta(days=1)
```

---

### 决策 11：批量指标计算

**选择**：按 365 天/批计算指标，每批加载 `batch_start - LOOKBACK_DAYS` 到 `batch_end` 的数据

**理由**：
- 技术指标（如 MA300）需要前 300 天的数据作为窗口
- 每批加载 `LOOKBACK_DAYS + batch_days` 的数据，确保指标计算准确
- 每批完成后更新 `indicator_date`

**实现**：
```python
async def compute_indicators_in_batches(
    code: str, start_date: date, end_date: date,
    batch_days: int = 365, lookback_days: int = 300
) -> None:
    """按批次计算指标，每批在事务中完成写入 + 更新进度。"""
    current = start_date
    while current <= end_date:
        batch_end = min(current + timedelta(days=batch_days - 1), end_date)
        # 加载 lookback 窗口的数据
        data_start = current - timedelta(days=lookback_days)
        data = await load_daily_data(code, data_start, batch_end)
        indicators = compute_indicators(data, current, batch_end)
        # 事务：批量写入指标 + 更新 indicator_date
        async with session.begin():
            await bulk_upsert_indicators(session, code, indicators)
            await update_indicator_progress(session, code, batch_end)
        current = batch_end + timedelta(days=1)
```

---

### 决策 12：盘后链路改造

**选择**：盘后链路使用进度表驱动，分阶段执行

**流程**：
```python
async def run_post_market_chain(target_date):
    # 获取同步锁，防止与启动流程/retry job 并发
    if not await acquire_sync_lock():
        logger.warning("[盘后链路] 另一个同步流程正在运行，跳过")
        return

    try:
        # 阶段 0：交易日历更新
        await calendar_step()

        # 阶段 1：更新股票列表 + 初始化进度表
        await sync_stock_list()
        await reset_stale_status()
        await init_sync_progress()

        # 阶段 2：批量处理（数据 + 指标），带超时控制
        stocks = await get_stocks_needing_sync(target_date)
        await process_stocks_batch(stocks, target_date,
                                   timeout=settings.sync_batch_timeout)

        # 阶段 3：完整性门控 + 策略执行
        summary = await get_sync_summary(target_date)
        if summary["completion_rate"] >= threshold:
            await cache_refresh_step()
            await pipeline_step(target_date)
        else:
            logger.warning("[盘后链路] 完成率 %.1f%%，跳过策略", ...)

        # 阶段 4：完整性告警
        await check_pipeline_completeness(target_date)
    finally:
        await release_sync_lock()
```

---

### 决策 13：退市检测的事务处理

**选择**：发现股票退市时，使用数据库事务同时更新 stocks 表和 stock_sync_progress 表

**理由**：
- 退市涉及两张表的状态变更，必须保证原子性
- 如果只更新了 stocks 但 progress 未标记 delisted，该股票仍会参与同步（浪费 API 调用）
- 如果只更新了 progress 但 stocks 未更新，其他模块读到的退市信息不一致

**实现**：
```python
async def mark_stock_delisted(ts_code: str, delist_date: date) -> None:
    """事务：同时更新 stocks 表退市信息 + progress 表状态。"""
    async with session.begin():
        # 1. 更新 stocks 表
        await session.execute(
            update(Stock).where(Stock.ts_code == ts_code).values(
                delist_date=delist_date,
                list_status='D',
            )
        )
        # 2. 更新 progress 表
        await session.execute(
            update(StockSyncProgress).where(
                StockSyncProgress.ts_code == ts_code
            ).values(
                status='delisted',
                updated_at=func.now(),
            )
        )
```

**批量退市处理**（在 init_sync_progress 中）：
```python
async def sync_delisted_status() -> dict:
    """对比 stocks 表，双向同步退市状态。返回 {newly_delisted, restored} 数量。"""
    async with session.begin():
        # 正向：stocks 已退市但 progress 未标记 → 标记 delisted
        delisted_result = await session.execute(
            update(StockSyncProgress)
            .where(
                StockSyncProgress.ts_code.in_(
                    select(Stock.ts_code).where(Stock.delist_date.isnot(None))
                ),
                StockSyncProgress.status != 'delisted',
            )
            .values(status='delisted', updated_at=func.now())
        )
        # 反向：stocks 取消退市但 progress 仍为 delisted → 恢复 idle
        restored_result = await session.execute(
            update(StockSyncProgress)
            .where(
                StockSyncProgress.ts_code.in_(
                    select(Stock.ts_code).where(Stock.delist_date.is_(None))
                ),
                StockSyncProgress.status == 'delisted',
            )
            .values(status='idle', updated_at=func.now())
        )
        return {
            "newly_delisted": delisted_result.rowcount,
            "restored": restored_result.rowcount,
        }
```

**触发时机**：
- `init_sync_progress()` 执行后，调用 `sync_delisted_status()` 批量同步退市状态
- 更新股票列表时，发现新退市股票立即调用 `mark_stock_delisted()`

---

## Risks / Trade-offs

### 风险 1：启动时间增加

**风险**：启动时更新股票列表 + 从进度表恢复同步会增加启动时间

**缓解措施**：
- 可通过 `SYNC_STOCK_LIST_ON_STARTUP=false` 跳过股票列表更新
- 可通过 `SKIP_INTEGRITY_CHECK=true` 完全跳过同步
- 断点续传：只处理未完成的股票，不重复处理

### 风险 2：BaoStock API 限流

**风险**：补齐大量缺失数据时可能触发 API 限流

**缓解措施**：
- 使用现有连接池机制（复用登录会话）
- 使用 Semaphore 控制并发
- 重试时降低并发数
- 按批次处理，每批更新进度

### 风险 3：BaoStock 连接池并发安全

**风险**：连接池 `_created_count < self._size` 检查无锁保护

**缓解措施**：
- 在 `acquire()` 中使用 `asyncio.Lock` 保护 `_created_count` 的检查和递增操作

### 风险 4：status 卡死（进程崩溃恢复）

**风险**：进程在处理某只股票时崩溃，该股票的 status 停留在 `syncing` 或 `computing`，永远无法被正常流程选中

**缓解措施**：
- 启动时和盘后链路开始时调用 `reset_stale_status()`，将 `syncing`/`computing` 重置为 `idle`
- 因为进程已重启，不可能还有正在处理的任务，重置是安全的

### 风险 5：并发执行冲突

**风险**：启动时的 `sync_from_progress()`、盘后链路的 `run_post_market_chain()`、20:00 的 `retry_failed_stocks_job()` 可能同时运行，导致同一只股票被两个流程同时处理

**缓解措施**：
- 使用 Redis 锁（`SETNX sync_lock`）保证同一时间只有一个同步流程在运行
- 获取锁失败时记录日志并跳过，等待下次触发
- 锁设置 TTL（如 4 小时），防止持有者崩溃后锁永不释放

### 风险 6：failed 股票被重复处理

**风险**：`get_stocks_needing_sync` 如果不排除 `failed`，盘后链路和 retry job 会同时处理同一只 failed 股票

**缓解措施**：
- `get_stocks_needing_sync` 排除 `failed`：`WHERE status NOT IN ('delisted', 'failed')`
- failed 股票只由 retry job 处理，职责分离
- 盘后链路中新产生的失败标记为 `failed`，等待 retry job 处理

### 风险 7：永久失败的股票

**风险**：某些股票在 BaoStock 上确实无数据（如已退市但未标记），retry job 每天重试形成死循环

**缓解措施**：
- `stock_sync_progress` 增加 `retry_count` 字段
- 超过 `batch_sync_max_retries`（默认 2）次后不再自动重试
- 日志中记录达到上限的股票，提醒人工介入

### 风险 8：退市状态反转

**风险**：极少数情况下 BaoStock 更正数据，取消某只股票的退市状态。如果 progress 表中仍为 `delisted`，该股票永远不会被同步

**缓解措施**：
- `sync_delisted_status()` 增加反向逻辑：stocks 表 delist_date 为 NULL 但 progress 为 delisted → 恢复为 idle

### 风险 9：盘后链路超时

**风险**：大量股票需要同步时（如首次部署），盘后链路可能运行数小时，影响第二天的调度

**缓解措施**：
- `process_stocks_batch` 增加整体超时控制（`sync_batch_timeout`，默认 4 小时）
- 超时后记录已完成的进度，未完成的股票下次继续（断点续传天然支持）
- 日志记录超时信息，便于运维排查

### 权衡 1：批次大小选择

**权衡**：批次越大，API 调用越少，但单次失败影响越大

**选择**：365 天/批，可通过 `sync_batch_days` 配置调整

### 权衡 2：环境隔离粒度

**权衡**：完全隔离（不同数据库）vs 逻辑隔离（同库不同 schema）

**选择**：物理隔离（不同数据库 + Redis db），最简单可靠

---

## Migration Plan

### 部署步骤

**步骤 1：创建环境配置文件**
```bash
# 创建生产环境配置
cp .env .env.prod
# 编辑 .env.prod，确认 DATABASE_URL 和 REDIS_DB

# 创建测试环境配置（可选）
cp .env .env.test
# 编辑 .env.test，使用不同的数据库和 Redis db
```

**步骤 2：数据库迁移**
```bash
uv run alembic upgrade head
```

**步骤 3：首次启动**
```bash
# 首次启动会自动初始化进度表，所有股票 data_date=1900-01-01
# 然后从 data_start_date 开始按批次同步
uv run uvicorn app.main:app
```

### 回滚策略

```bash
# 跳过同步快速启动
SKIP_INTEGRITY_CHECK=true uv run uvicorn app.main:app

# 完全回滚
git checkout master
uv run uvicorn app.main:app
```

---

## Open Questions

1. **`data_start_date` 的默认值**
   - 当前设为 `2024-01-01`，是否需要更早？
   - 建议：根据用户需求配置，默认 2 年足够

2. **指数类股票的处理**
   - 停止更新的指数如何识别？
   - 建议：V2 再优化，当前按普通股票处理
