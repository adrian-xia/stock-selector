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

### Requirement: P5 核心数据同步方法
DataManager SHALL 提供 P5 核心扩展数据的同步方法集，包括约 20 张表的 raw 数据拉取和 2 张业务表的 ETL 清洗。所有 sync_raw 方法 SHALL 复用已有的 `_upsert_raw` 通用方法写入 raw 表。

#### Scenario: P5 同步方法可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 sync_raw_suspend_d、sync_raw_limit_list_d、sync_raw_margin 等 P5 核心同步方法

#### Scenario: P5 ETL 方法可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 etl_suspend、etl_limit_list 方法用于业务表清洗

#### Scenario: P5 聚合入口可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 sync_p5_core 聚合方法，一次调用完成所有 P5 核心数据同步
