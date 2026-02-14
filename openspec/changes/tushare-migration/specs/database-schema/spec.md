## ADDED Requirements

### Requirement: 新增 raw_tushare_* 原始表
数据库 SHALL 新增 98 张 raw_tushare_* 原始表，每个 Tushare 接口一一对应（排除实时接口、重复接口和不可用接口），通过 Alembic 迁移脚本创建。详细清单见 raw-data-layer spec。

#### Scenario: 迁移脚本执行
- **WHEN** 执行 alembic upgrade head
- **THEN** 所有 98 张 raw_tushare_* 表和指数/板块业务表创建成功

### Requirement: 新增指数业务表
数据库 SHALL 新增 index_basic, index_daily, index_weight, industry_classify, industry_member, index_technical_daily 六张指数业务表。

#### Scenario: 指数表结构正确
- **WHEN** 查看 index_daily 表
- **THEN** 包含 ts_code/trade_date/open/high/low/close/vol/amount/pct_chg 字段，主键为 (ts_code, trade_date)

#### Scenario: 指数技术指标表结构正确
- **WHEN** 查看 index_technical_daily 表
- **THEN** 字段结构与 technical_daily 完全一致（23 个指标），主键为 (ts_code, trade_date)

### Requirement: 新增板块业务表
数据库 SHALL 新增 concept_index, concept_daily, concept_member, concept_technical_daily 四张板块业务表。

#### Scenario: 板块表结构正确
- **WHEN** 查看 concept_index 表
- **THEN** 包含 ts_code/name/source/type 字段，source 区分 ths/dc/tdx

#### Scenario: 板块技术指标表结构正确
- **WHEN** 查看 concept_technical_daily 表
- **THEN** 字段结构与 technical_daily 完全一致（23 个指标），主键为 (ts_code, trade_date)
