## Context

当前系统的数据写入存在两条并行路径：

1. **直接路径**（P0 日线）：`sync_from_progress` / `process_stocks_batch` → 直接写 `stock_daily`，绕过 raw 层
2. **raw-first 路径**（P2-P5）：`sync_raw_*` → `raw_tushare_*` → `etl_*` → 业务表

这导致 raw 层数据不完整（raw_tushare_daily 仅 24 万行 vs stock_daily 374 万行），无法作为可靠的数据基础。此外，`batch_insert` 使用 `DO NOTHING` 策略，Tushare 历史数据修正无法同步到业务表。COPY 协议因临时表不存在始终失败，降级到逐行 INSERT 影响性能。

**现有代码结构：**
- `app/data/manager.py` — DataManager，包含所有 sync_raw_* / etl_* 方法
- `app/data/etl.py` — ETL 转换函数（transform_tushare_*）+ batch_insert
- `app/data/copy_writer.py` — COPY 协议批量写入
- `app/scheduler/jobs.py` — 盘后链路 run_post_market_chain
- `app/scheduler/core.py` — 启动同步 sync_from_progress
- `scripts/init_data.py` — 数据初始化向导

## Goals / Non-Goals

**Goals:**
- 统一所有数据链路为 `API → raw_* → ETL → 业务表` 的单一流程
- 抽象统一同步入口，初始化/增量/续传/重试复用同一套代码
- raw_* 表成为全量、最新的数据基础，支撑任意数据处理和预测
- 修复 COPY 协议、P3/P4/P5 同步失败等已知问题
- ETL 写入策略统一为 DO UPDATE，支持数据修正同步

**Non-Goals:**
- 不改变业务表结构和 API 接口
- 不新增 raw 表（使用现有 98 张 raw 表）
- 不改变前端交互
- 不处理 Tushare VIP 接口权限问题（接口不可用的记录日志跳过）

## Decisions

### D1: 统一同步入口设计

**决策**：在 DataManager 中新增 `sync_raw_tables(table_group, date_range, mode)` 方法作为统一入口。

```
sync_raw_tables(
    table_group: str | list[str],  # "p0" / "p1" / ["p0", "p2"] / "all"
    start_date: date,
    end_date: date,
    mode: str = "incremental",     # "full" / "incremental" / "gap_fill"
    concurrency: int = 4,
)
```

**流程**：
1. 根据 table_group 确定需要同步的 raw 表集合
2. 根据 mode 确定日期范围（full=全量, incremental=最新, gap_fill=缺口）
3. 按日期循环：调用对应的 `sync_raw_*` 写入 raw 表
4. 调用对应的 `etl_*` 从 raw 表清洗到业务表

**替代方案**：保持现有分散的调用方式 → 拒绝，代码重复且容易遗漏步骤

### D2: raw 表缺口检测机制

**决策**：基于 `raw_sync_progress` 表记录每张 raw 表的同步进度（最新日期），启动时对比交易日历检测缺口。

```sql
-- raw_sync_progress 表结构
table_name VARCHAR(100) PRIMARY KEY,
last_sync_date DATE,
last_sync_rows INTEGER,
updated_at TIMESTAMPTZ
```

**检测逻辑**：
1. 查询 trade_calendar 获取所有交易日
2. 对比每张 raw 表的 last_sync_date
3. 缺口 = 交易日列表中 > last_sync_date 的日期
4. 对于非日频表（周/月/季度），按对应频率检测

**替代方案**：直接 COUNT(*) 对比 → 拒绝，大表全表扫描太慢

### D3: process_stocks_batch 改造为 raw-first

**决策**：将 `process_stocks_batch` 内部的 `sync_daily`（直接写 stock_daily）替换为 `sync_raw_daily` + `etl_daily`。

**改造点**：
- `process_single_stock` 内部调用 `sync_raw_daily(ts_code, start, end)` 写入 raw_tushare_daily/adj_factor/daily_basic
- 然后调用 `etl_daily(ts_code, start, end)` 从 raw 表清洗到 stock_daily
- `stock_sync_progress` 的 data_date 更新逻辑不变

**替代方案**：新建独立的 raw-first 同步方法 → 拒绝，会导致两套并行代码

### D4: COPY 协议修复

**决策**：`copy_writer.py` 中的临时表创建逻辑有 bug，需要在 COPY 前显式创建临时表。

```python
# 修复：在 raw connection 上创建临时表
await raw_conn.execute(f"""
    CREATE TEMP TABLE IF NOT EXISTS _tmp_{table_name}
    (LIKE {table_name} INCLUDING ALL) ON COMMIT DROP
""")
```

**替代方案**：放弃 COPY 协议只用 INSERT → 拒绝，COPY 性能优势明显（10x+）

### D5: batch_insert 统一为 DO UPDATE

**决策**：`batch_insert` 的 `on_conflict_do_nothing()` 改为 `on_conflict_do_update()`，与 `_upsert_raw` 保持一致。

**影响**：ETL 写入业务表时，如果 raw 表数据有更新（如复权因子调整），业务表也会同步更新。

### D6: 盘后链路 raw 追平策略

**决策**：盘后链路在步骤 3 之后增加"raw 追平"步骤，检测所有 raw 表是否追到目标日期，未追平的自动补同步。

**执行顺序**：
1. 步骤 0-3：现有流程（改为 raw-first）
2. 步骤 3.1（新）：P1 财务数据同步（按季度）
3. 步骤 3.5-3.8：现有 P2-P5 同步
4. 步骤 3.9（改）：raw 追平检查 — 扫描 raw_sync_progress，补齐遗漏
5. 步骤 4-6：缓存/策略/AI（不变）

### D7: 数据初始化脚本重构

**决策**：`scripts/init_data.py` 重构为调用 `sync_raw_tables("all", start, end, mode="full")`，不再有独立的写入逻辑。

**流程**：
1. 用户选择日期范围
2. 调用 `sync_raw_tables("p0", start, end, mode="full")` — 股票列表 + 日历 + 日线
3. 调用 `sync_raw_tables("p1", start, end, mode="full")` — 财务数据
4. 调用 `sync_raw_tables("p2", start, end, mode="full")` — 资金流向
5. 调用 `sync_raw_tables("p3", start, end, mode="full")` — 指数
6. 调用 `sync_raw_tables("p4", start, end, mode="full")` — 板块
7. 调用 `sync_raw_tables("p5", start, end, mode="full")` — 补充数据
8. 全量计算技术指标

## Risks / Trade-offs

- **[API 调用量大幅增加]** → raw 表全量补齐需要大量 Tushare API 调用，可能触发限流。缓解：使用令牌桶限流（已有 400 QPS），按日期批量获取全市场数据减少调用次数
- **[首次 raw 补齐耗时长]** → 从 2006 年补齐所有 raw 表可能需要数小时。缓解：支持断点续传（raw_sync_progress），可分多次完成
- **[raw-first 路径增加写入延迟]** → 每条数据多一次 raw 表写入。缓解：COPY 协议修复后批量写入性能可接受
- **[DO UPDATE 可能覆盖手动修正]** → 如果业务表有手动修正的数据，ETL 重跑会覆盖。缓解：当前系统无手动修正场景，raw 表数据即真实数据
- **[P5 部分接口不可用]** → 12 项 P5 同步失败，部分可能是 VIP 接口。缓解：失败项记录日志并跳过，不阻断链路

## Migration Plan

1. **Phase 1 — 基础设施**：修复 COPY 协议、batch_insert DO UPDATE、创建 raw_sync_progress 表
2. **Phase 2 — 统一入口**：实现 sync_raw_tables 统一方法，修复 P3/P4/P5 已知问题
3. **Phase 3 — 路径改造**：process_stocks_batch 改为 raw-first，sync_from_progress 改为 raw 缺口检测
4. **Phase 4 — 盘后链路**：增加 P1 步骤、raw 追平检查
5. **Phase 5 — 初始化脚本**：重构 init_data.py 复用统一入口
6. **Phase 6 — 数据补齐**：运行全量 raw 补齐，验证数据一致性

**回滚策略**：业务表结构不变，如需回滚可恢复旧的直接写入路径

## Open Questions

- P5 失败的 12 项中，哪些是 VIP 接口限制、哪些是代码 bug？需要逐项排查
- raw 表全量补齐的优先级：是否先补 P0（日线），再逐步补 P1-P5？
- `raw_tushare_stock_basic` 和 `raw_tushare_trade_cal` 是否需要纳入 raw-first（当前直接写业务表，数据量小且变更少）
