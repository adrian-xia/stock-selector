## Context

`stock_daily` 表已有 `adj_factor DECIMAL(16,6)` 字段，但全部为 NULL。原因是 BaoStock 日线接口 (`query_history_k_data_plus`, `adjustflag="3"`) 仅返回不复权价格，不提供复权因子。

回测引擎 `load_stock_data()` 已实现前复权逻辑（`price * adj_factor / latest_adj_factor`），但在 `adj_factor` 为 NULL 时自动跳过。数据库表结构无需变更，只需填充数据。

BaoStock 提供独立的 `bs.query_adjust_factor(code, start_date, end_date)` 接口，返回每个交易日的前复权因子（`foreAdjustFactor`）和后复权因子（`backAdjustFactor`）。

现有 CLI 模式：`cli.py` 使用 Click，每个命令遍历股票列表，逐只调用 `BaoStockClient` 方法，每 100 只打印进度。

## Goals / Non-Goals

**Goals:**

- 填充 `stock_daily.adj_factor` 字段，使回测引擎的前复权逻辑生效
- 提供全量导入命令（首次填充约 5000 只股票的历史复权因子）
- 提供增量同步能力（每日盘后自动补充当日复权因子）
- 复用现有 `BaoStockClient` 的重试、限流、线程池机制

**Non-Goals:**

- 不引入 Tushare 作为复权因子备用数据源（V2 考虑）
- 不修改 `stock_daily` 表结构（字段已存在）
- 不修改回测引擎代码（前复权逻辑已就绪）
- 不实现 `import_progress` 断点续传表（V1 简化，用 `WHERE adj_factor IS NULL` 跳过已有数据）

## Decisions

### D1: 使用 BaoStock `query_adjust_factor()` 而非前复权价格反算

**选择**: 直接调用 `bs.query_adjust_factor()` 获取复权因子。

**备选方案**:
- A) 用 `adjustflag="2"` 获取前复权价格，再反算因子 → 精度损失，且无法获得原始因子
- B) 引入 Tushare Pro `adj_factor` 接口 → 需要额外 API Token，增加依赖

**理由**: BaoStock 已有专用接口，无需额外依赖，返回的 `foreAdjustFactor` 可直接写入 `adj_factor` 字段。

### D2: 批量 UPDATE 而非 INSERT

**选择**: 用 `UPDATE stock_daily SET adj_factor = :val WHERE ts_code = :code AND trade_date = :date` 批量更新。

**理由**: `stock_daily` 记录已存在（日线导入时创建），只需填充 `adj_factor` 字段。使用 `executemany` 批量提交，每只股票一次事务。

### D3: 全量导入用 `WHERE adj_factor IS NULL` 实现幂等

**选择**: 全量导入时先查询 `adj_factor IS NULL` 的股票列表，跳过已填充的。

**备选方案**: 引入 `import_progress` 表记录进度 → 过度设计

**理由**: 简单有效，重跑时自动跳过已完成的股票。除权除息日的历史因子变更通过 `--force` 参数覆盖。

### D4: 增量同步嵌入 `sync-daily` 流程

**选择**: 在 `sync-daily` 命令中，日线数据同步完成后自动调用复权因子同步。

**备选方案**: 独立定时任务 → 增加调度复杂度

**理由**: 复权因子与日线数据强关联，同步时机一致，减少调度配置。

## Risks / Trade-offs

**[BaoStock QPS 限制]** → 全量导入约 5000 只股票，每只一次 API 调用。按现有 QPS 限制（默认 3），预计 30-60 分钟。可通过调大 `baostock_qps_limit` 加速。

**[除权除息日历史因子变更]** → 当股票发生除权除息时，BaoStock 会更新该股票所有历史日期的复权因子。增量同步仅更新当日因子，不会自动回溯。→ 提供 `--force` 参数强制全量刷新单只股票；定期（如每月）全量刷新一次。

**[BaoStock 数据延迟]** → 复权因子可能在盘后 16:00-17:00 才更新。→ 增量同步安排在 17:00 之后执行（与日线同步一致）。
