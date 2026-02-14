## ADDED Requirements

### Requirement: 系统应判断股票在指定日期是否应该有数据

系统 SHALL 根据股票的上市日期和退市日期，判断该股票在指定交易日是否应该有数据。

#### Scenario: 判断未上市的股票
- **WHEN** 某股票上市日期为 2026-02-10，查询日期为 2026-02-05
- **THEN** 系统判定该股票不应该有数据（还未上市）

#### Scenario: 判断已退市的股票
- **WHEN** 某股票退市日期为 2026-02-05，查询日期为 2026-02-10
- **THEN** 系统判定该股票不应该有数据（已退市）

#### Scenario: 判断正常交易的股票
- **WHEN** 某股票上市日期为 2020-01-01，退市日期为空，查询日期为 2026-02-10
- **THEN** 系统判定该股票应该有数据

#### Scenario: 判断上市当天的股票
- **WHEN** 某股票上市日期为 2026-02-10，查询日期为 2026-02-10
- **THEN** 系统判定该股票应该有数据（上市当天）

### Requirement: 系统应基于 progress.status 筛选待同步股票

系统 SHALL 在查询待同步股票时，直接按 `stock_sync_progress.status` 字段筛选，排除 `delisted` 状态的股票，无需 JOIN stocks 表。

#### Scenario: 排除 delisted 状态的股票
- **WHEN** 查询待同步股票，有 1058 只股票 status='delisted'
- **THEN** 系统直接通过 `WHERE status NOT IN ('delisted')` 排除，不参与同步

#### Scenario: 完成率计算排除 delisted
- **WHEN** 计算完成率，8000 只股票中 1000 只为 delisted
- **THEN** 系统以 7000 只非 delisted 股票为基数计算完成率

### Requirement: 系统应通过事务处理退市状态变更

系统 SHALL 在发现股票退市时，使用数据库事务同时更新 stocks 表和 stock_sync_progress 表，保证数据一致性。

#### Scenario: 单只股票退市事务处理
- **WHEN** 发现某股票退市
- **THEN** 系统在同一事务中更新 stocks 表（delist_date + list_status='D'）和 progress 表（status='delisted'）

#### Scenario: 批量同步退市状态
- **WHEN** init_sync_progress() 执行后
- **THEN** 系统在事务中批量将 stocks 表中已退市但 progress 表中未标记 delisted 的股票状态同步

#### Scenario: 记录退市处理统计
- **WHEN** 批量同步退市状态完成
- **THEN** 系统记录日志：新标记 delisted 的股票数量
