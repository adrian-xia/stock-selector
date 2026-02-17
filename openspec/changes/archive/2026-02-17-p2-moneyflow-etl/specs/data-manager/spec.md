## ADDED Requirements

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
