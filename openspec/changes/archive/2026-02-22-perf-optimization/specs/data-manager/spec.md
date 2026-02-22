## MODIFIED Requirements

### Requirement: 按日期全市场同步模式
DataManager SHALL 提供 `sync_raw_daily(trade_date)` 方法，一次性获取全市场当日数据（daily + adj_factor + daily_basic），写入 raw 表。写入 SHALL 优先使用 COPY 协议，失败时降级到 INSERT。

#### Scenario: 全市场日线同步
- **WHEN** 调用 `sync_raw_daily(date(2026, 2, 14))`
- **THEN** 发起 3 次 Tushare API 调用（daily + adj_factor + daily_basic），将原始数据通过 COPY 协议写入对应 raw 表

#### Scenario: COPY 降级时正常完成
- **WHEN** 调用 `sync_raw_daily(date(2026, 2, 14))` 且 COPY 协议不可用
- **THEN** SHALL 降级到 INSERT 方式写入 raw 表，功能不受影响

### Requirement: ETL 从 raw 表到业务表
DataManager SHALL 提供 `etl_daily(trade_date)` 方法，从 raw 表读取数据，清洗后写入 stock_daily 业务表。写入 SHALL 优先使用 COPY 协议。

#### Scenario: ETL 转换
- **WHEN** 调用 `etl_daily(date(2026, 2, 14))`
- **THEN** 从 raw_tushare_daily + raw_tushare_adj_factor + raw_tushare_daily_basic 三表 JOIN，清洗后通过 COPY 协议写入 stock_daily

### Requirement: 资金流向原始数据同步
DataManager SHALL 提供 `sync_raw_moneyflow(trade_date)` 方法，按日期获取全市场个股资金流向数据写入 raw_tushare_moneyflow 表；提供 `sync_raw_top_list(trade_date)` 方法，获取龙虎榜明细和机构明细写入对应 raw 表。写入 SHALL 优先使用 COPY 协议。

#### Scenario: 同步资金流向
- **WHEN** 调用 `sync_raw_moneyflow(date(2026, 2, 16))`
- **THEN** 从 Tushare moneyflow 接口获取数据，通过 COPY 协议写入 raw_tushare_moneyflow 表

#### Scenario: 同步龙虎榜
- **WHEN** 调用 `sync_raw_top_list(date(2026, 2, 16))`
- **THEN** 从 Tushare top_list 和 top_inst 接口获取数据，通过 COPY 协议写入对应 raw 表

### Requirement: P5 核心数据同步方法
DataManager SHALL 提供 P5 核心扩展数据的同步方法集，包括约 20 张表的 raw 数据拉取和 2 张业务表的 ETL 清洗。所有 sync_raw 方法 SHALL 优先使用 COPY 协议写入 raw 表，复用 `copy_insert()` 或降级到 `_upsert_raw`。

#### Scenario: P5 同步方法可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 sync_raw_suspend_d、sync_raw_limit_list_d、sync_raw_margin 等 P5 核心同步方法

#### Scenario: P5 ETL 方法可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 etl_suspend、etl_limit_list 方法用于业务表清洗

#### Scenario: P5 聚合入口可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 sync_p5_core 聚合方法，一次调用完成所有 P5 核心数据同步
