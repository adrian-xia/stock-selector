# 复权因子采集 & 最低佣金补全 — 开发计划

> 来源：Phase 4 回测准确性验证中发现的两个问题
> 优先级：P1（影响回测准确性）

---

## 问题 1：复权因子缺失

### 现状
- `stock_daily.adj_factor` 字段全部为 NULL（共 11,160,233 条记录）
- BaoStock 日线接口 (`query_history_k_data_plus`, `adjustflag="3"`) 返回不复权价格，**不提供复权因子**
- `load_stock_data()` 在 `adj_factor` 为 NULL 时跳过前复权，回测使用不复权价格
- 对有除权除息的股票（如分红、送股），回测结果会出现价格跳空，导致收益计算不准确

### 方案
使用 BaoStock `query_adjust_factor()` 接口单独获取复权因子。

### 任务

- [x] **1.1** 在 `app/data/baostock.py` 中新增 `fetch_adj_factor(code, start_date, end_date)` 方法
  - 实现：`_fetch_adj_factor_sync()` 同步方法 + `fetch_adj_factor()` 异步公开方法
  - 调用 `bs.query_adjust_factor()`，解析 `foreAdjustFactor` 字段
  - 返回 `list[dict]`（含 `ts_code`, `trade_date`, `adj_factor`）

- [x] **1.2** 在 `app/data/cli.py` 中新增 `sync-adj-factor` 命令
  - 遍历所有上市股票，调用 `fetch_adj_factor()`
  - 批量 UPDATE `stock_daily.adj_factor`（按 ts_code + trade_date 匹配）
  - 支持 `--force` 参数（强制覆盖已有数据）
  - 跳过已有 adj_factor 的股票（`--force` 时不跳过），每 100 只打印进度

- [x] **1.3** 在 `app/data/cli.py` 的 `sync-daily` 命令中集成复权因子同步
  - 每只股票日线同步完成后，自动调用 `fetch_adj_factor` 获取当日复权因子并更新

- [x] **1.4** 执行全量复权因子导入
  - 运行 `uv run python -m app.data.cli sync-adj-factor`
  - 实际耗时：约 1.5 小时
  - 填充结果：5,187 只个股全部完成（88.4% 填充率）
  - 缺失的 1,954 只为指数/ETF/基金（BaoStock 不提供复权因子，符合预期）

- [x] **1.5** 验证复权因子正确性
  - 抽查 600519.SH（贵州茅台，14 次除权）、600028.SH（中国石化，13 次除权）、600016.SH（民生银行，8 次除权）
  - 前复权后除权日涨跌幅均在 ±2% 内，价格连续无跳空
  - 对 600519.SH 执行回测，确认收益计算正确（总收益 -9.46%，最大回撤 10.76%）

- [x] **1.6** 补充单元测试
  - `test_baostock_adj_factor.py`：测试复权因子获取（返回格式、字段类型、代码转换）
  - `test_adj_factor_update.py`：测试批量更新（正确写入、无匹配行、大批量自动分片）
  - `test_cli_adj_factor.py`：测试 CLI 命令（参数解析、跳过逻辑、`--force` 覆盖）
  - `test_sync_daily_adj.py`：测试增量同步流程包含复权因子步骤

### 设计文档已更新
- `01-详细设计-数据采集.md` §3 复权处理：补充了 BaoStock 复权因子数据源说明

---

## 问题 2：最低佣金 5 元

### 现状
- `ChinaStockCommission` 代码中**已实现**最低佣金 5 元（`min_commission=5.0`）
- 但设计文档 `03-详细设计-AI与回测.md` 中未体现此参数
- Phase 4 验证已确认最低佣金逻辑正确

### 任务

- [x] **2.1** 更新设计文档 `03-详细设计-AI与回测.md` §2.1 核心配置
  - ~~已完成：添加 `min_commission=5.0` 参数和注释~~

> 此问题仅为文档补全，代码无需修改。

---

## 执行顺序

```
1.1 (baostock 接口) → 1.2 (CLI 命令) → 1.4 (全量导入) → 1.5 (验证)
                    → 1.3 (增量同步)
                    → 1.6 (单元测试)
```

## 影响范围

| 文件 | 变更类型 |
|------|---------|
| `app/data/baostock.py` | 新增 `_fetch_adj_factor_sync()` + `fetch_adj_factor()` |
| `app/data/adj_factor.py` | 新增 `batch_update_adj_factor()` |
| `app/data/cli.py` | 新增 `sync-adj-factor` 命令，`sync-daily` 集成复权因子同步 |
| `tests/unit/test_baostock_adj_factor.py` | 新增 |
| `tests/unit/test_adj_factor_update.py` | 新增 |
| `tests/unit/test_cli_adj_factor.py` | 新增 |
| `tests/unit/test_sync_daily_adj.py` | 新增 |
| `README.md` | 更新数据采集命令说明 |
| `scripts/verify_adj_factor.py` | 新增（验证脚本） |
| `scripts/verify_backtest_adj.py` | 新增（回测验证脚本） |
