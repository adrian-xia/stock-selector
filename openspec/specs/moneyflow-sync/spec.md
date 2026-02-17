## Requirements

### Requirement: 资金流向原始数据同步
系统 SHALL 提供 `DataManager.sync_raw_moneyflow(trade_date)` 方法，按日期从 Tushare API 获取个股资金流向数据并写入 `raw_tushare_moneyflow` 表。使用 ON CONFLICT DO UPDATE 避免重复数据。

#### Scenario: 正常同步
- **WHEN** 调用 `sync_raw_moneyflow(date(2026, 2, 16))`
- **THEN** 从 Tushare moneyflow 接口获取 2026-02-16 全市场数据，写入 raw_tushare_moneyflow 表，返回 `{"moneyflow": <count>}`

#### Scenario: 非交易日
- **WHEN** 调用 `sync_raw_moneyflow` 传入非交易日
- **THEN** API 返回空数据，方法返回 `{"moneyflow": 0}`

### Requirement: 龙虎榜原始数据同步
系统 SHALL 提供 `DataManager.sync_raw_top_list(trade_date)` 方法，按日期从 Tushare API 获取龙虎榜明细和机构明细数据，分别写入 `raw_tushare_top_list` 和 `raw_tushare_top_inst` 表。

#### Scenario: 正常同步
- **WHEN** 调用 `sync_raw_top_list(date(2026, 2, 16))`
- **THEN** 从 Tushare top_list 和 top_inst 接口获取数据，写入对应 raw 表，返回 `{"top_list": <count>, "top_inst": <count>}`

### Requirement: 资金流向 ETL 清洗入库
系统 SHALL 提供 `DataManager.etl_moneyflow(trade_date)` 方法，从 raw 表读取数据，调用 ETL 清洗函数，写入 `money_flow` 和 `dragon_tiger` 业务表。

#### Scenario: 正常 ETL
- **WHEN** 调用 `etl_moneyflow(date(2026, 2, 16))`，且 raw 表中有该日期数据
- **THEN** 清洗后写入 money_flow 和 dragon_tiger 业务表，返回 `{"money_flow": <count>, "dragon_tiger": <count>}`

#### Scenario: raw 表无数据
- **WHEN** 调用 `etl_moneyflow` 但 raw 表中无该日期数据
- **THEN** 返回 `{"money_flow": 0, "dragon_tiger": 0}`

### Requirement: 盘后链路集成
盘后链路 SHALL 在批量数据拉取（步骤 3）之后、缓存刷新（步骤 4）之前，增加资金流向同步步骤。该步骤调用 `sync_raw_moneyflow` + `sync_raw_top_list` + `etl_moneyflow`。失败不阻断后续链路。

#### Scenario: 正常执行
- **WHEN** 盘后链路执行到资金流向同步步骤
- **THEN** 依次调用 sync_raw_moneyflow、sync_raw_top_list、etl_moneyflow，记录日志

#### Scenario: 同步失败
- **WHEN** 资金流向同步步骤中任一方法抛出异常
- **THEN** 记录错误日志，继续执行后续步骤（缓存刷新、策略管道）
