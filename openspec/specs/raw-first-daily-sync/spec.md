## ADDED Requirements

### Requirement: 统一同步入口 sync_raw_tables
DataManager SHALL 提供 `sync_raw_tables(table_group, start_date, end_date, mode, concurrency)` 方法作为所有数据同步的统一入口。

#### Scenario: 按分组同步
- **WHEN** 调用 `sync_raw_tables("p0", date(2026,2,13), date(2026,2,13))`
- **THEN** 系统依次执行 P0 相关的 sync_raw_* 方法写入 raw 表，再执行 etl_* 清洗到业务表

#### Scenario: 全量同步
- **WHEN** 调用 `sync_raw_tables("all", date(2006,1,1), date(2026,2,13), mode="full")`
- **THEN** 系统按 P0 → P1 → P2 → P3 → P4 → P5 顺序，对每个交易日执行完整的 raw 同步 + ETL

#### Scenario: 缺口填充模式
- **WHEN** 调用 `sync_raw_tables("p0", start, end, mode="gap_fill")`
- **THEN** 系统仅同步 raw_sync_progress 中标记为缺失的日期，跳过已同步的日期

### Requirement: P0 日线数据 raw-first 路径
P0 日线数据（daily/adj_factor/daily_basic）的同步 SHALL 先写入 raw_tushare_* 表，再通过 ETL 清洗到 stock_daily。

#### Scenario: 单只股票同步
- **WHEN** process_single_stock 同步某只股票的日线数据
- **THEN** 数据先写入 raw_tushare_daily、raw_tushare_adj_factor、raw_tushare_daily_basic，再通过 etl_daily 写入 stock_daily

#### Scenario: 按日期批量同步
- **WHEN** 按日期批量获取全市场日线数据
- **THEN** 数据先写入 raw 表，再批量 ETL 到 stock_daily

### Requirement: 股票列表和交易日历 raw-first
sync_stock_list 和 sync_trade_calendar SHALL 先写入 raw_tushare_stock_basic / raw_tushare_trade_cal，再 ETL 到 stocks / trade_calendar。

#### Scenario: 股票列表同步
- **WHEN** 调用 sync_stock_list
- **THEN** 数据先写入 raw_tushare_stock_basic，再 ETL 到 stocks 表

#### Scenario: 交易日历同步
- **WHEN** 调用 sync_trade_calendar
- **THEN** 数据先写入 raw_tushare_trade_cal，再 ETL 到 trade_calendar 表
