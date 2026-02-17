## 1. 业务表模型与迁移

- [x] 1.1 在 `app/models/` 中新增 `suspend_info` 业务表 ORM 模型（ts_code, trade_date, suspend_type, suspend_timing, data_source）
- [x] 1.2 在 `app/models/` 中新增 `limit_list_daily` 业务表 ORM 模型（ts_code, trade_date, limit, pct_chg, amp, fc_ratio, fl_ratio, fd_amount, first_time, last_time, open_times, strth, limit_amount, data_source）
- [x] 1.3 创建 Alembic 迁移脚本，生成 suspend_info 和 limit_list_daily 两张业务表

## 2. ETL Transform 函数

- [x] 2.1 在 `app/data/etl.py` 中新增 `transform_tushare_suspend_d` 函数，将 raw_tushare_suspend_d 数据清洗为 suspend_info 格式
- [x] 2.2 在 `app/data/etl.py` 中新增 `transform_tushare_limit_list_d` 函数，将 raw_tushare_limit_list_d 数据清洗为 limit_list_daily 格式

## 3. DataManager 日频同步方法

- [x] 3.1 新增 `sync_raw_suspend_d(trade_date)` 和 `sync_raw_limit_list_d(trade_date)` 方法
- [x] 3.2 新增 `sync_raw_margin(trade_date)` 和 `sync_raw_margin_detail(trade_date)` 方法
- [x] 3.3 新增 `sync_raw_block_trade(trade_date)` 和 `sync_raw_daily_share(trade_date)` 方法
- [x] 3.4 新增 `sync_raw_stk_factor(trade_date)` 和 `sync_raw_stk_factor_pro(trade_date)` 方法
- [x] 3.5 新增 `sync_raw_hm_board(trade_date)` 和 `sync_raw_hm_list(trade_date)` 方法
- [x] 3.6 新增 `sync_raw_ths_hot(trade_date)`、`sync_raw_dc_hot(trade_date)` 和 `sync_raw_ths_limit(trade_date)` 方法

## 4. DataManager 周频/月频/静态同步方法

- [x] 4.1 新增 `sync_raw_weekly(trade_date)` 和 `sync_raw_monthly(trade_date)` 方法
- [x] 4.2 新增 `sync_raw_stock_company()` 和 `sync_raw_margin_target()` 静态同步方法
- [x] 4.3 新增 `sync_raw_top10_holders(trade_date)`、`sync_raw_top10_floatholders(trade_date)`、`sync_raw_stk_holdernumber(trade_date)` 和 `sync_raw_stk_holdertrade(trade_date)` 季度同步方法

## 5. DataManager ETL 与聚合方法

- [x] 5.1 新增 `etl_suspend(trade_date)` 方法，从 raw 表读取 → transform → 写入 suspend_info
- [x] 5.2 新增 `etl_limit_list(trade_date)` 方法，从 raw 表读取 → transform → 写入 limit_list_daily
- [x] 5.3 新增 `sync_p5_core(trade_date)` 聚合方法，按频率分组调用所有 P5 核心同步和 ETL 方法

## 6. 盘后链路集成

- [x] 6.1 在 `app/scheduler/jobs.py` 的 `run_post_market_chain` 中添加步骤 3.8（P5 核心数据同步），调用 `manager.sync_p5_core(target)`，失败不阻断后续链路

## 7. 文档更新

- [x] 7.1 更新 `docs/design/99-实施范围-V1与V2划分.md`，标注 P5 核心 ETL 为"✅ V1 已实施"
- [x] 7.2 更新 `CLAUDE.md` 和 `README.md`，同步 P5 核心 ETL 相关说明
