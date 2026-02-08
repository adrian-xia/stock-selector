## Why

Phase 4 回测准确性验证发现 `stock_daily.adj_factor` 全部为 NULL（11,160,233 条记录）。BaoStock 日线接口 (`adjustflag="3"`) 仅返回不复权价格，不提供复权因子。回测引擎在 `adj_factor` 缺失时跳过前复权，对有除权除息的股票（分红、送股）会出现价格跳空，导致收益计算不准确。

## What Changes

- **新增复权因子采集能力**：调用 BaoStock `query_adjust_factor()` 接口，获取每只股票每个交易日的前复权因子，写入 `stock_daily.adj_factor` 字段
- **新增 CLI 命令 `sync-adj-factor`**：支持全量导入和增量同步复权因子
- **修改数据源客户端接口**：`DataSourceClient` 新增 `fetch_adj_factor()` 方法
- **修改增量同步流程**：日线行情同步完成后自动补充当日复权因子

## Capabilities

### New Capabilities

- `adj-factor-sync`: 复权因子采集与同步能力，包括 BaoStock 复权因子查询接口封装、全量/增量同步 CLI 命令、写入 `stock_daily.adj_factor` 字段

### Modified Capabilities

- `data-source-clients`: `DataSourceClient` 接口新增 `fetch_adj_factor(code, start_date, end_date)` 方法；`BaoStockClient` 实现该方法，调用 `bs.query_adjust_factor()`
- `data-import-scripts`: 新增 `sync-adj-factor` CLI 子命令，支持全量导入复权因子（遍历所有上市股票，批量 UPDATE）

## Impact

| 范围 | 影响 |
|------|------|
| `app/data/baostock.py` | 新增 `fetch_adj_factor()` 方法 |
| `app/data/cli.py` | 新增 `sync-adj-factor` 子命令 |
| `app/data/etl.py` | 增量同步流程增加复权因子步骤 |
| `tests/unit/` | 新增复权因子采集和前复权计算测试 |
| `README.md` | 更新数据采集命令说明 |
| 数据库 | `stock_daily.adj_factor` 字段从 NULL 填充为实际值 |
| 回测引擎 | 无代码变更，`load_stock_data()` 已有前复权逻辑，填充数据后自动生效 |
