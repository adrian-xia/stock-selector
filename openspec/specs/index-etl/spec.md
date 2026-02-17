## Requirements

### Requirement: 指数日线原始数据同步
DataManager SHALL 提供 `sync_raw_index_daily(trade_date)` 方法，遍历核心指数列表，按日期从 Tushare index_daily 接口获取指数日线行情数据写入 raw_tushare_index_daily 表。

#### Scenario: 正常同步
- **WHEN** 调用 `sync_raw_index_daily(date(2026, 2, 17))`
- **THEN** 遍历核心指数列表，逐个调用 fetch_raw_index_daily 获取当日数据，写入 raw_tushare_index_daily 表，返回 `{"index_daily": <count>}`

#### Scenario: 非交易日
- **WHEN** 调用 `sync_raw_index_daily` 传入非交易日
- **THEN** API 返回空数据，方法返回 `{"index_daily": 0}`

### Requirement: 指数成分股权重原始数据同步
DataManager SHALL 提供 `sync_raw_index_weight(trade_date)` 方法，按日期从 Tushare index_weight 接口获取核心指数成分股权重数据写入 raw_tushare_index_weight 表。

#### Scenario: 正常同步
- **WHEN** 调用 `sync_raw_index_weight(date(2026, 2, 17))`
- **THEN** 遍历核心指数列表，获取成分股权重数据，写入 raw_tushare_index_weight 表，返回 `{"index_weight": <count>}`

### Requirement: 指数技术因子原始数据同步
DataManager SHALL 提供 `sync_raw_index_technical(trade_date)` 方法，按日期从 Tushare index_factor_pro 接口获取指数技术因子数据写入 raw_tushare_index_factor_pro 表。

#### Scenario: 正常同步
- **WHEN** 调用 `sync_raw_index_technical(date(2026, 2, 17))`
- **THEN** 遍历核心指数列表，获取技术因子数据，写入 raw_tushare_index_factor_pro 表，返回 `{"index_factor_pro": <count>}`

### Requirement: 指数静态数据同步
DataManager SHALL 提供 `sync_raw_index_basic()` 方法获取全部指数基础信息、`sync_raw_industry_classify()` 方法获取行业分类、`sync_raw_industry_member()` 方法获取行业成分股，分别写入对应 raw 表。这些方法为全量刷新，不按日期过滤。

#### Scenario: 同步指数基础信息
- **WHEN** 调用 `sync_raw_index_basic()`
- **THEN** 从 Tushare index_basic 接口获取全部指数信息，写入 raw_tushare_index_basic 表，返回 `{"index_basic": <count>}`

#### Scenario: 同步行业分类
- **WHEN** 调用 `sync_raw_industry_classify()`
- **THEN** 从 Tushare index_classify 接口获取行业分类数据，写入 raw_tushare_index_classify 表，返回 `{"index_classify": <count>}`

#### Scenario: 同步行业成分股
- **WHEN** 调用 `sync_raw_industry_member()`
- **THEN** 从 Tushare index_member_all 接口获取行业成分股数据，写入 raw_tushare_index_member_all 表，返回 `{"index_member_all": <count>}`

### Requirement: 指数数据 ETL 清洗入库
DataManager SHALL 提供 `etl_index(trade_date)` 方法，从 raw 表读取指数日线、成分股权重和技术因子数据，调用 ETL 清洗函数，写入 index_daily、index_weight 和 index_technical_daily 业务表。

#### Scenario: 正常 ETL
- **WHEN** 调用 `etl_index(date(2026, 2, 17))`，且 raw 表中有该日期数据
- **THEN** 清洗后写入 index_daily、index_weight、index_technical_daily 业务表，返回 `{"index_daily": <count>, "index_weight": <count>, "index_technical_daily": <count>}`

#### Scenario: raw 表无数据
- **WHEN** 调用 `etl_index` 但 raw 表中无该日期数据
- **THEN** 返回 `{"index_daily": 0, "index_weight": 0, "index_technical_daily": 0}`

### Requirement: 指数静态数据 ETL 清洗入库
DataManager SHALL 提供 `etl_index_static()` 方法，从 raw 表读取指数基础信息、行业分类和行业成分股数据，清洗后写入 index_basic、industry_classify 和 industry_member 业务表。

#### Scenario: 正常 ETL
- **WHEN** 调用 `etl_index_static()`
- **THEN** 清洗后写入 index_basic、industry_classify、industry_member 业务表，返回 `{"index_basic": <count>, "industry_classify": <count>, "industry_member": <count>}`
