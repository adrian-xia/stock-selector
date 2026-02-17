## ADDED Requirements

### Requirement: P5 核心 raw 数据日频同步
DataManager SHALL 提供以下日频同步方法，按日期获取全市场数据写入对应 raw 表：
- `sync_raw_suspend_d(trade_date)` — 停复牌信息
- `sync_raw_limit_list_d(trade_date)` — 涨跌停统计
- `sync_raw_margin(trade_date)` — 融资融券汇总
- `sync_raw_margin_detail(trade_date)` — 融资融券明细
- `sync_raw_block_trade(trade_date)` — 大宗交易
- `sync_raw_daily_share(trade_date)` — 每日股本
- `sync_raw_stk_factor(trade_date)` — 技术因子
- `sync_raw_stk_factor_pro(trade_date)` — 技术因子Pro
- `sync_raw_hm_board(trade_date)` — 热门板块
- `sync_raw_hm_list(trade_date)` — 热门股票
- `sync_raw_ths_hot(trade_date)` — 同花顺热股
- `sync_raw_dc_hot(trade_date)` — 东财热股
- `sync_raw_ths_limit(trade_date)` — 同花顺涨跌停

每个方法 SHALL 调用对应的 TushareClient.fetch_raw_xxx 方法获取数据，通过 `_upsert_raw` 写入 raw 表。

#### Scenario: 日频数据同步
- **WHEN** 调用 `sync_raw_suspend_d(date(2026, 2, 17))`
- **THEN** 从 Tushare suspend_d 接口获取当日停复牌数据，写入 raw_tushare_suspend_d 表

#### Scenario: 批量日频同步
- **WHEN** 盘后链路步骤 3.8 触发
- **THEN** 依次调用所有日频同步方法，每个方法独立执行，单个失败不影响其他

### Requirement: P5 核心 raw 数据周频同步
DataManager SHALL 提供 `sync_raw_weekly(trade_date)` 方法，获取周线行情写入 raw_tushare_weekly 表。

#### Scenario: 周线同步
- **WHEN** 调用 `sync_raw_weekly(date(2026, 2, 14))`（周五）
- **THEN** 从 Tushare weekly 接口获取当周数据，写入 raw_tushare_weekly 表

### Requirement: P5 核心 raw 数据月频同步
DataManager SHALL 提供 `sync_raw_monthly(trade_date)` 方法获取月线行情。

#### Scenario: 月线同步
- **WHEN** 调用 `sync_raw_monthly(date(2026, 2, 28))`（月末）
- **THEN** 从 Tushare monthly 接口获取当月数据，写入 raw_tushare_monthly 表

### Requirement: P5 核心 raw 数据静态同步
DataManager SHALL 提供以下静态/低频同步方法：
- `sync_raw_stock_company()` — 上市公司基本信息
- `sync_raw_margin_target()` — 融资融券标的
- `sync_raw_top10_holders(trade_date)` — 十大股东（按季度）
- `sync_raw_top10_floatholders(trade_date)` — 十大流通股东（按季度）
- `sync_raw_stk_holdernumber(trade_date)` — 股东户数（按季度）
- `sync_raw_stk_holdertrade(trade_date)` — 股东增减持

#### Scenario: 静态数据全量同步
- **WHEN** 调用 `sync_raw_stock_company()`
- **THEN** 从 Tushare stock_company 接口获取全量数据，写入 raw_tushare_stock_company 表

#### Scenario: 季度数据同步
- **WHEN** 调用 `sync_raw_top10_holders(date(2026, 2, 17))`
- **THEN** 从 Tushare top10_holders 接口获取数据，写入 raw_tushare_top10_holders 表

### Requirement: 停复牌业务表 ETL
DataManager SHALL 提供 `etl_suspend(trade_date)` 方法，从 raw_tushare_suspend_d 读取数据，通过 `transform_tushare_suspend_d` 清洗后写入 suspend_info 业务表。

#### Scenario: 停复牌 ETL
- **WHEN** 调用 `etl_suspend(date(2026, 2, 17))`
- **THEN** 从 raw_tushare_suspend_d 读取当日数据，清洗日期格式和字段映射，写入 suspend_info 业务表

### Requirement: 涨跌停统计业务表 ETL
DataManager SHALL 提供 `etl_limit_list(trade_date)` 方法，从 raw_tushare_limit_list_d 读取数据，通过 `transform_tushare_limit_list_d` 清洗后写入 limit_list_daily 业务表。

#### Scenario: 涨跌停 ETL
- **WHEN** 调用 `etl_limit_list(date(2026, 2, 17))`
- **THEN** 从 raw_tushare_limit_list_d 读取当日数据，清洗后写入 limit_list_daily 业务表

### Requirement: P5 聚合同步入口
DataManager SHALL 提供 `sync_p5_core(trade_date)` 聚合方法，按频率分组依次调用所有 P5 核心同步和 ETL 方法，返回汇总结果。

#### Scenario: 聚合同步
- **WHEN** 调用 `sync_p5_core(date(2026, 2, 17))`
- **THEN** 依次执行日频 raw 同步 → 停复牌 ETL → 涨跌停 ETL，返回各步骤结果汇总
