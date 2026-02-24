## Context

当前系统有两个数据同步入口：

1. **启动同步**（`sync_from_progress`，`app/scheduler/core.py`）：服务启动时执行，当前只同步最近一个交易日的 P0 数据（通过 `get_stocks_needing_sync` + `process_stocks_batch`），然后对 P2/P3/P5 执行 `gap_fill`。不覆盖 P0 多日缺口、P1 财务数据、P4 板块数据。
2. **盘后链路**（`run_post_market_chain`，`app/scheduler/jobs.py`）：每日 15:30 触发，按 P0→P1→P2→P3→P4→P5 顺序同步当天数据（`mode="incremental"`），最后有一个 `gap_fill` 步骤扫描 `raw_sync_progress` 补齐遗漏表。但如果某天盘后链路整体未执行（停机），该天数据不会被后续链路补回。

现有基础设施：
- `manager.detect_missing_dates(start, end)` — 对比交易日历和 `stock_daily` 表，返回缺失的交易日列表
- `manager.sync_raw_tables(group, start, end, mode="gap_fill")` — 基于 `raw_sync_progress` 表跳过已同步日期
- `manager.sync_raw_daily(date)` + `manager.etl_daily(date)` — P0 单日同步
- 配置项 `data_start_date`、`data_integrity_check_enabled`、`data_integrity_check_days`

## Goals / Non-Goals

**Goals:**

- 服务启动时自动检测并补齐 P0~P5 全优先级的历史缺口，无需人工干预
- 盘后链路执行完当天 incremental 同步后，回溯检测近 N 天缺口并补齐，防止单日失败导致永久数据空洞
- 提供统一的缺口补齐函数，供启动同步和盘后链路复用
- 通过配置项控制补齐行为（启用开关、回溯天数），避免启动时间过长

**Non-Goals:**

- 不改变 `copy_writer.py` 的 UPSERT 逻辑（`fetched_at` 排除行为保持不变）
- 不改变 `init_data.py` 全量初始化脚本的逻辑
- 不引入新的数据库表或模型
- 不改变盘后链路的触发时间和整体编排顺序

## Decisions

### 1. 启动同步：P0 缺口用 `detect_missing_dates` 检测，逐日补齐

**选择**：调用 `detect_missing_dates(data_start_date, target_date)` 获取缺失交易日列表，逐日执行 `sync_raw_daily` + `etl_daily`。

**替代方案**：直接用 `sync_raw_tables("p0", ..., mode="gap_fill")` 基于 `raw_sync_progress` 补齐。

**理由**：`detect_missing_dates` 直接对比 `stock_daily` 业务表和交易日历，检测结果更准确（反映 ETL 后的实际状态）。`raw_sync_progress` 只记录 raw 表写入进度，不能保证 ETL 也成功了。

### 2. 启动同步：P1~P5 统一使用 `sync_raw_tables` 的 `gap_fill` 模式

**选择**：对 P1/P2/P3/P4/P5 统一调用 `sync_raw_tables(group, data_start, target_date, mode="gap_fill")`，基于 `raw_sync_progress` 表跳过已同步日期。

**理由**：这些优先级的 raw 表已有 `raw_sync_progress` 追踪机制，`gap_fill` 模式天然支持断点续传。P4 板块数据需要额外处理板块成分股（`sync_concept_member`），在 gap_fill 后单独补齐。

### 3. 盘后链路：incremental 之后追加近 N 天回溯

**选择**：在盘后链路现有的步骤 3.85（`raw 追平检查`）中，将 `gap_fill` 的范围从仅当天扩展为 `target_date - N 天 ~ target_date`，N 通过配置项 `GAP_FILL_LOOKBACK_DAYS` 控制，默认 7 天。

**替代方案**：每次盘后链路都从 `data_start_date` 开始全量 gap_fill。

**理由**：全量扫描太慢，7 天回溯足以覆盖周末 + 偶发失败场景。如果停机超过 7 天，启动同步会兜底补齐。

### 4. 新增配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `GAP_FILL_ENABLED` | `true` | 启动时是否执行全量缺口补齐 |
| `GAP_FILL_LOOKBACK_DAYS` | `7` | 盘后链路回溯检测天数 |

### 5. 执行顺序

启动同步的补齐顺序：P0（逐日）→ P1（按季度）→ P2 → P3 → P4 → P5（均 gap_fill）。与盘后链路保持一致的优先级顺序。每个步骤失败不阻断后续步骤。

## Risks / Trade-offs

- **启动时间变长** → 通过 `GAP_FILL_ENABLED` 开关控制，紧急启动时可设为 false 或使用 `SKIP_INTEGRITY_CHECK=true` 跳过
- **API 调用量增加**（停机多天后启动会集中拉取大量数据）→ 令牌桶限流（400 QPS）已有保护，不会超限；P0 逐日同步每天约 1 秒，30 天缺口约 30 秒
- **P1 财务数据缺口检测复杂**（按季度而非按日）→ 复用盘后链路的季度判断逻辑，检测当前季度是否已同步，未同步则补拉
- **P4 板块成分股无 `raw_sync_progress` 追踪** → 板块成分股通过 `sync_concept_member` 按概念代码同步，不依赖日期维度，启动时检查 `concept_member` 表是否为空来决定是否补拉
