## ADDED Requirements

### Requirement: 概念板块列表表
系统 SHALL 提供 `concept_index` 业务表，统一存储同花顺/东方财富/通达信三个数据源的概念和行业板块列表，通过 `source` 字段区分数据源。

#### Scenario: 查询同花顺概念板块
- **WHEN** 查询 source='ths' 的概念板块
- **THEN** 返回同花顺全部概念板块列表（代码/名称/类型）

#### Scenario: 查询东方财富概念板块
- **WHEN** 查询 source='dc' 的概念板块
- **THEN** 返回东方财富全部概念板块列表

### Requirement: 概念板块日线行情表
系统 SHALL 提供 `concept_daily` 业务表，存储板块日线行情数据。

#### Scenario: 查询板块日线行情
- **WHEN** 查询某概念板块在指定日期的行情
- **THEN** 返回 open/high/low/close/vol/pct_chg 等字段

### Requirement: 概念板块成分股表
系统 SHALL 提供 `concept_member` 业务表，存储板块与个股的映射关系。

#### Scenario: 查询某概念板块的成分股
- **WHEN** 查询"人工智能"概念板块的成分股
- **THEN** 返回该板块下所有股票代码

#### Scenario: 查询某股票所属的概念板块
- **WHEN** 查询 600519.SH 所属的概念板块
- **THEN** 返回该股票所属的全部概念板块列表

### Requirement: 板块技术指标表
系统 SHALL 提供 `concept_technical_daily` 业务表，存储概念/行业板块的技术指标数据。字段结构与个股 `technical_daily` 完全一致（23 个指标：MA5-MA250、MACD、KDJ、RSI、BOLL、VOL_MA、ATR14），主键为 (ts_code, trade_date)。

#### Scenario: 查询板块技术指标
- **WHEN** 查询某概念板块在 2026-02-14 的技术指标
- **THEN** 返回 ma5/ma10/ma20/ma60/macd_dif/macd_dea/kdj_k/rsi6/boll_upper 等 23 个指标字段

#### Scenario: 板块技术指标计算
- **WHEN** 板块日线行情数据写入 concept_daily 后
- **THEN** 复用 indicator.py 的计算函数，基于 concept_daily 的 OHLCV 数据计算 23 个技术指标，写入 concept_technical_daily

### Requirement: 板块数据同步方法
DataManager SHALL 提供板块数据同步方法：`sync_concept_index(source)`, `sync_concept_daily(source, trade_date)`, `sync_concept_member(source)`, `update_concept_indicators(trade_date)`。

#### Scenario: 同步同花顺板块数据
- **WHEN** 调用 `sync_concept_index(source='ths')`
- **THEN** 从 Tushare ths_index 接口获取数据，写入 raw 表并 ETL 到 concept_index 业务表

#### Scenario: 计算板块技术指标
- **WHEN** 调用 `update_concept_indicators(date(2026, 2, 14))`
- **THEN** 基于 concept_daily 数据计算全部板块的 23 个技术指标，写入 concept_technical_daily
