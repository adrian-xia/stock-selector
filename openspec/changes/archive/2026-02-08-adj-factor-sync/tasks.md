## 1. BaoStockClient 新增 fetch_adj_factor

- [x] 1.1 在 `app/data/baostock.py` 中新增 `_fetch_adj_factor_sync(code, start_date, end_date)` 同步方法，调用 `bs.query_adjust_factor()`，解析返回的 `foreAdjustFactor` 字段，返回 `list[dict]`（含 `ts_code`, `trade_date`, `adj_factor`）
- [x] 1.2 在 `app/data/baostock.py` 中新增 `fetch_adj_factor(code, start_date, end_date)` 异步公开方法，通过 `_with_retry` 包装同步方法，复用重试和限流机制
- [x] 1.3 新增 `tests/unit/test_baostock_adj_factor.py`，测试 `fetch_adj_factor` 的返回格式、字段类型、代码转换，mock BaoStock API

## 2. 批量更新 adj_factor 到 stock_daily

- [x] 2.1 在 `app/data/manager.py`（或新建 `app/data/adj_factor.py`）中实现 `batch_update_adj_factor(session_factory, ts_code, records)` 函数，批量 UPDATE `stock_daily.adj_factor`，自动分片适配 asyncpg 32767 参数限制
- [x] 2.2 新增单元测试，验证批量更新正确写入、无匹配行时不报错、大批量自动分片

## 3. CLI 命令 sync-adj-factor

- [x] 3.1 在 `app/data/cli.py` 中新增 `sync-adj-factor` Click 命令，支持 `--force` 参数
- [x] 3.2 实现全量导入逻辑：查询所有上市股票，跳过已有 `adj_factor` 的股票（`--force` 时不跳过），逐只调用 `fetch_adj_factor` + `batch_update_adj_factor`，每 100 只打印进度，最终打印 success/failed 汇总
- [x] 3.3 新增单元测试，验证 CLI 命令参数解析、跳过逻辑、`--force` 覆盖逻辑

## 4. 增量同步集成

- [x] 4.1 修改 `app/data/cli.py` 的 `sync-daily` 命令，在每只股票日线同步完成后，调用 `fetch_adj_factor` 获取当日复权因子并更新 `stock_daily.adj_factor`
- [x] 4.2 新增单元测试，验证 `sync-daily` 流程包含复权因子同步步骤

## 5. 验证与文档

- [x] 5.1 运行 `uv run python -m app.data.cli sync-adj-factor` 执行全量导入，确认 `stock_daily.adj_factor` 填充完成
- [x] 5.2 验证回测前复权生效：对有除权除息的股票（600519.SH、600028.SH、600016.SH）验证前复权价格连续性，并对 600519.SH 执行回测确认收益计算正确
- [x] 5.3 更新 `README.md`，在数据采集命令说明中添加 `sync-adj-factor` 命令
- [x] 5.4 更新 `/Users/adrian/Developer/Codes/stock-selector/PLAN_adj_factor_and_commission.md`，将已完成的任务标记为 `[x]`，同步最终实现状态
