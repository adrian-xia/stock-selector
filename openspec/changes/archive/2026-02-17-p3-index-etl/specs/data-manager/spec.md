## ADDED Requirements

### Requirement: 指数日线原始数据同步
DataManager SHALL 提供 `sync_raw_index_daily(trade_date)` 方法，遍历核心指数列表按日期获取指数日线行情写入 raw_tushare_index_daily 表；提供 `sync_raw_index_weight(trade_date)` 方法获取成分股权重写入 raw_tushare_index_weight 表；提供 `sync_raw_index_technical(trade_date)` 方法获取技术因子写入 raw_tushare_index_factor_pro 表。

#### Scenario: 同步指数日线
- **WHEN** 调用 `sync_raw_index_daily(date(2026, 2, 17))`
- **THEN** 遍历核心指数列表，从 Tushare index_daily 接口获取数据，写入 raw_tushare_index_daily 表

#### Scenario: 同步成分股权重
- **WHEN** 调用 `sync_raw_index_weight(date(2026, 2, 17))`
- **THEN** 遍历核心指数列表，从 Tushare index_weight 接口获取数据，写入 raw_tushare_index_weight 表

#### Scenario: 同步技术因子
- **WHEN** 调用 `sync_raw_index_technical(date(2026, 2, 17))`
- **THEN** 遍历核心指数列表，从 Tushare index_factor_pro 接口获取数据，写入 raw_tushare_index_factor_pro 表

### Requirement: 指数静态数据同步
DataManager SHALL 提供 `sync_raw_index_basic()`、`sync_raw_industry_classify()`、`sync_raw_industry_member()` 方法，全量获取指数基础信息、行业分类和行业成分股写入对应 raw 表。

#### Scenario: 同步指数基础信息
- **WHEN** 调用 `sync_raw_index_basic()`
- **THEN** 从 Tushare index_basic 接口获取全部指数信息，写入 raw_tushare_index_basic 表

#### Scenario: 同步行业分类和成分股
- **WHEN** 调用 `sync_raw_industry_classify()` 和 `sync_raw_industry_member()`
- **THEN** 分别从 Tushare index_classify 和 index_member_all 接口获取数据，写入对应 raw 表

### Requirement: 指数数据 ETL 清洗入库
DataManager SHALL 提供 `etl_index(trade_date)` 方法从 raw 表清洗写入 index_daily、index_weight、index_technical_daily 业务表；提供 `etl_index_static()` 方法从 raw 表清洗写入 index_basic、industry_classify、industry_member 业务表。

#### Scenario: 日常 ETL
- **WHEN** 调用 `etl_index(date(2026, 2, 17))`
- **THEN** 从 raw 表读取当日数据，清洗后写入 index_daily、index_weight、index_technical_daily 业务表

#### Scenario: 静态数据 ETL
- **WHEN** 调用 `etl_index_static()`
- **THEN** 从 raw 表读取全量数据，清洗后写入 index_basic、industry_classify、industry_member 业务表
