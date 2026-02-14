## ADDED Requirements

### Requirement: 指数基础信息表
系统 SHALL 提供 `index_basic` 业务表，存储指数基础信息（代码/名称/发布商/类别/基期等）。

#### Scenario: 查询沪深300指数信息
- **WHEN** 查询 ts_code='000300.SH' 的指数信息
- **THEN** 返回名称、发布商（中证公司）、类别、基期等完整信息

### Requirement: 指数日线行情表
系统 SHALL 提供 `index_daily` 业务表，存储指数日线 OHLCV 行情数据。

#### Scenario: 查询指数日线行情
- **WHEN** 查询 000300.SH 在 2026-02-14 的行情
- **THEN** 返回 open/high/low/close/vol/amount/pct_chg 等字段

### Requirement: 指数成分权重表
系统 SHALL 提供 `index_weight` 业务表，存储各指数的成分股及权重（月度数据）。

#### Scenario: 查询沪深300成分股
- **WHEN** 查询 000300.SH 的最新成分股
- **THEN** 返回约 300 只成分股及其权重

### Requirement: 行业分类表
系统 SHALL 提供 `industry_classify` 业务表，存储申万/中信行业分类（支持三级分类）。

#### Scenario: 查询申万一级行业
- **WHEN** 查询 level='L1' 的申万行业分类
- **THEN** 返回 31 个一级行业（2021 版）

### Requirement: 行业成分股表
系统 SHALL 提供 `industry_member` 业务表，存储行业成分股映射关系。

#### Scenario: 查询某行业的成分股
- **WHEN** 查询银行行业的成分股
- **THEN** 返回该行业下所有股票代码

### Requirement: 指数技术指标表
系统 SHALL 提供 `index_technical_daily` 业务表，存储指数的技术指标数据。字段结构与个股 `technical_daily` 完全一致（23 个指标：MA5-MA250、MACD、KDJ、RSI、BOLL、VOL_MA、ATR14），主键为 (ts_code, trade_date)。

#### Scenario: 查询指数技术指标
- **WHEN** 查询 000300.SH 在 2026-02-14 的技术指标
- **THEN** 返回 ma5/ma10/ma20/ma60/macd_dif/macd_dea/kdj_k/rsi6/boll_upper 等 23 个指标字段

#### Scenario: 指数技术指标计算
- **WHEN** 指数日线行情数据写入 index_daily 后
- **THEN** 复用 indicator.py 的计算函数，基于 index_daily 的 OHLCV 数据计算 23 个技术指标，写入 index_technical_daily

### Requirement: 指数数据同步方法
DataManager SHALL 提供指数数据同步方法：`sync_index_basic()`, `sync_index_daily(trade_date)`, `sync_index_weight()`, `sync_industry_classify()`, `sync_industry_member()`, `update_index_indicators(trade_date)`。

#### Scenario: 同步指数日线行情
- **WHEN** 调用 `sync_index_daily(date(2026, 2, 14))`
- **THEN** 从 Tushare 获取全部指数当日行情，写入 raw 表并 ETL 到 index_daily 业务表

#### Scenario: 计算指数技术指标
- **WHEN** 调用 `update_index_indicators(date(2026, 2, 14))`
- **THEN** 基于 index_daily 数据计算全部指数的 23 个技术指标，写入 index_technical_daily
