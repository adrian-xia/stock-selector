## MODIFIED Requirements

### Requirement: DataManager 使用 TushareClient
DataManager SHALL 使用 TushareClient 作为唯一数据源客户端，`primary` 默认值从 "baostock" 改为 "tushare"。

#### Scenario: 默认使用 Tushare
- **WHEN** 创建 DataManager 实例不指定 primary
- **THEN** 默认使用 TushareClient

### Requirement: 按日期全市场同步模式
DataManager SHALL 提供 `sync_raw_daily(trade_date)` 方法，一次性获取全市场当日数据（daily + adj_factor + daily_basic），写入 raw 表。

#### Scenario: 全市场日线同步
- **WHEN** 调用 `sync_raw_daily(date(2026, 2, 14))`
- **THEN** 发起 3 次 Tushare API 调用（daily + adj_factor + daily_basic），将原始数据写入对应 raw 表

### Requirement: ETL 从 raw 表到业务表
DataManager SHALL 提供 `etl_daily(trade_date)` 方法，从 raw 表读取数据，清洗后写入 stock_daily 业务表。

#### Scenario: ETL 转换
- **WHEN** 调用 `etl_daily(date(2026, 2, 14))`
- **THEN** 从 raw_tushare_daily + raw_tushare_adj_factor + raw_tushare_daily_basic 三表 JOIN，清洗后写入 stock_daily

### Requirement: sync_stock_list 使用 Tushare
sync_stock_list() SHALL 调用 TushareClient.fetch_stock_list() 获取数据，使用 transform_tushare_stock_basic 清洗。

#### Scenario: 同步股票列表
- **WHEN** 调用 sync_stock_list()
- **THEN** 从 Tushare stock_basic 接口获取数据，清洗后写入 stocks 表

### Requirement: sync_trade_calendar 使用 Tushare
sync_trade_calendar() SHALL 调用 TushareClient.fetch_trade_calendar() 获取数据，使用 transform_tushare_trade_cal 清洗。

#### Scenario: 同步交易日历
- **WHEN** 调用 sync_trade_calendar()
- **THEN** 从 Tushare trade_cal 接口获取数据，清洗后写入 trade_calendar 表

### Requirement: 资金流向原始数据同步
DataManager SHALL 提供 `sync_raw_moneyflow(trade_date)` 方法，按日期获取全市场个股资金流向数据写入 raw_tushare_moneyflow 表；提供 `sync_raw_top_list(trade_date)` 方法，获取龙虎榜明细和机构明细写入对应 raw 表。

#### Scenario: 同步资金流向
- **WHEN** 调用 `sync_raw_moneyflow(date(2026, 2, 16))`
- **THEN** 从 Tushare moneyflow 接口获取数据，写入 raw_tushare_moneyflow 表

#### Scenario: 同步龙虎榜
- **WHEN** 调用 `sync_raw_top_list(date(2026, 2, 16))`
- **THEN** 从 Tushare top_list 和 top_inst 接口获取数据，写入对应 raw 表

### Requirement: 资金流向 ETL 清洗入库
DataManager SHALL 提供 `etl_moneyflow(trade_date)` 方法，从 raw 表读取资金流向和龙虎榜数据，清洗后写入 money_flow 和 dragon_tiger 业务表。

#### Scenario: ETL 转换
- **WHEN** 调用 `etl_moneyflow(date(2026, 2, 16))`
- **THEN** 从 raw_tushare_moneyflow 和 raw_tushare_top_list 读取数据，清洗后写入 money_flow 和 dragon_tiger 业务表
