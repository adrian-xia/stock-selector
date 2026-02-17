## ADDED Requirements

### Requirement: P2 资金流向数据校验
测试体系 SHALL 提供 P2 资金流向数据的完整性、ETL 转换正确性和数据质量校验。

#### Scenario: raw_tushare_moneyflow 记录数校验
- **WHEN** 查询最近一个交易日的 raw_tushare_moneyflow 数据
- **THEN** 记录数 SHALL >= 上市股票数 × 0.90

#### Scenario: moneyflow ETL 字段映射校验
- **WHEN** 对比 raw_tushare_moneyflow 和 money_flow 业务表同一条记录
- **THEN** ts_code、trade_date 映射正确，日期格式从 YYYYMMDD 转为 date 类型

#### Scenario: money_flow 关键字段非空率校验
- **WHEN** 查询最近一个交易日的 money_flow 业务表
- **THEN** buy_sm_amount、sell_sm_amount 等关键金额字段非空率 SHALL >= 90%

#### Scenario: dragon_tiger 数据校验
- **WHEN** 查询 raw_tushare_top_list 有数据的交易日
- **THEN** dragon_tiger 业务表 SHALL 有对应记录，且 raw → 业务表匹配度 >= 95%

### Requirement: P3 指数数据校验
测试体系 SHALL 提供 P3 指数数据的完整性、ETL 转换正确性和数据质量校验。

#### Scenario: raw_tushare_index_daily 记录数校验
- **WHEN** 查询最近一个交易日的 raw_tushare_index_daily 数据
- **THEN** 核心指数（上证综指、深证成指、沪深300 等）SHALL 全部有记录

#### Scenario: index_daily ETL 转换校验
- **WHEN** 对比 raw_tushare_index_daily 和 index_daily 业务表
- **THEN** 收盘价、成交量等字段映射正确，日期格式转换正确

#### Scenario: index_weight 数据校验
- **WHEN** 查询 raw_tushare_index_weight 数据
- **THEN** index_weight 业务表 SHALL 有对应记录，权重之和接近 100%

#### Scenario: index_basic 静态数据校验
- **WHEN** 查询 index_basic 业务表
- **THEN** 核心指数 SHALL 全部存在，name 字段非空

#### Scenario: industry_classify 数据校验
- **WHEN** 查询 industry_classify 业务表
- **THEN** 记录数 SHALL >= 20（申万一级行业数），行业名称非空

### Requirement: P4 板块数据校验
测试体系 SHALL 提供 P4 板块数据的完整性、ETL 转换正确性和数据质量校验。

#### Scenario: concept_index 数据校验
- **WHEN** 查询 concept_index 业务表
- **THEN** 记录数 SHALL >= 100（同花顺概念板块数），板块名称非空

#### Scenario: concept_daily 记录数校验
- **WHEN** 查询最近一个交易日的 concept_daily 数据
- **THEN** 记录数 SHALL >= concept_index 板块数 × 0.90

#### Scenario: concept_member 数据校验
- **WHEN** 查询 concept_member 业务表
- **THEN** 记录数 SHALL >= 1000，ts_code 格式正确

#### Scenario: concept_daily ETL 转换校验
- **WHEN** 对比 raw 表和 concept_daily 业务表同一条记录
- **THEN** 收盘价、涨跌幅等字段映射正确

### Requirement: P5 扩展数据校验
测试体系 SHALL 提供 P5 核心扩展数据的完整性、ETL 转换正确性和数据质量校验。

#### Scenario: raw_tushare_suspend_d 数据校验
- **WHEN** 查询有停牌数据的交易日
- **THEN** raw_tushare_suspend_d SHALL 有记录，ts_code 和 suspend_date 非空

#### Scenario: suspend_info ETL 转换校验
- **WHEN** 对比 raw_tushare_suspend_d 和 suspend_info 业务表
- **THEN** 字段映射正确，日期格式转换正确，raw → 业务表匹配度 >= 95%

#### Scenario: raw_tushare_limit_list_d 数据校验
- **WHEN** 查询最近一个交易日的 raw_tushare_limit_list_d 数据
- **THEN** SHALL 有记录（每个交易日都有涨跌停股票），ts_code 和 trade_date 非空

#### Scenario: limit_list_daily ETL 转换校验
- **WHEN** 对比 raw_tushare_limit_list_d 和 limit_list_daily 业务表
- **THEN** 字段映射正确，raw → 业务表匹配度 >= 95%

#### Scenario: P5 raw 表基础校验
- **WHEN** 查询 P5 日频 raw 表（margin、block_trade、daily_share 等）
- **THEN** 最近一个交易日 SHALL 有数据记录

### Requirement: 综合跨表一致性校验
测试体系 SHALL 提供跨优先级的数据一致性和时间连续性校验。

#### Scenario: 时间连续性校验
- **WHEN** 查询最近 5 个交易日的 stock_daily 数据
- **THEN** 每个交易日 SHALL 都有数据，无缺失日期

#### Scenario: stock_daily 与 index_daily 交易日一致性
- **WHEN** 对比 stock_daily 和 index_daily 最近 5 个交易日
- **THEN** 两表覆盖的交易日 SHALL 完全一致

#### Scenario: stock_daily 与 money_flow 交易日一致性
- **WHEN** 对比 stock_daily 和 money_flow 最近 5 个交易日
- **THEN** money_flow 覆盖的交易日 SHALL 是 stock_daily 交易日的子集

#### Scenario: stocks 表与 stock_daily ts_code 一致性
- **WHEN** 查询 stock_daily 最近一个交易日的 ts_code 集合
- **THEN** 所有 ts_code SHALL 在 stocks 表中存在

#### Scenario: index_daily 与 index_basic 指数代码一致性
- **WHEN** 查询 index_daily 最近一个交易日的指数代码
- **THEN** 所有指数代码 SHALL 在 index_basic 表中存在

#### Scenario: concept_daily 与 concept_index 板块代码一致性
- **WHEN** 查询 concept_daily 最近一个交易日的板块代码
- **THEN** 所有板块代码 SHALL 在 concept_index 表中存在

#### Scenario: raw_tushare_daily 三表 JOIN 完整性
- **WHEN** 查询最近一个交易日的 raw_tushare_daily、raw_tushare_adj_factor、raw_tushare_daily_basic
- **THEN** 三表按 (ts_code, trade_date) JOIN 的匹配率 SHALL >= 95%

#### Scenario: 全链路数据新鲜度
- **WHEN** 查询各业务表最新数据日期
- **THEN** stock_daily、money_flow、index_daily、concept_daily 的最新日期 SHALL 在最近 3 个交易日内
