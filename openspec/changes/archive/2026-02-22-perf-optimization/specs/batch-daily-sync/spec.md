## MODIFIED Requirements

### Requirement: 批量同步改为按日期模式
batch_sync_daily SHALL 改为按日期批量同步模式：给定一组交易日期，逐日调用 sync_raw_daily + etl_daily，替代原有的逐只股票同步模式。

#### Scenario: 批量同步多个交易日
- **WHEN** 调用 batch_sync_daily(trade_dates=[date(2026,2,13), date(2026,2,14)])
- **THEN** 逐日执行 sync_raw_daily + etl_daily，每日仅 3-4 次 API 调用

#### Scenario: 使用 TushareClient 限流
- **WHEN** 调用 batch_sync_daily
- **THEN** 使用 TushareClient 的令牌桶限流，无需连接池参数

## ADDED Requirements

### Requirement: 全量导入集成索引管理
batch_sync_daily SHALL 在全量导入模式（backfill）下集成索引管理：导入前删除非主键索引，导入完成后重建。日常增量同步不触发索引管理。

#### Scenario: 全量导入启用索引管理
- **WHEN** 调用 `batch_sync_daily(trade_dates, full_import=True)`
- **THEN** SHALL 在导入开始前调用 `drop_indexes()` 删除 stock_daily、technical_daily 等表的非主键索引
- **AND** 导入完成后 SHALL 调用 `rebuild_indexes()` 重建所有被删除的索引
- **AND** SHALL 记录索引管理的总耗时

#### Scenario: 日常增量同步不触发索引管理
- **WHEN** 调用 `batch_sync_daily(trade_dates)` 且未指定 full_import=True
- **THEN** SHALL 不执行索引删除和重建操作

#### Scenario: 导入异常时仍重建索引
- **WHEN** 全量导入过程中发生异常
- **THEN** SHALL 在 finally 中重建索引
- **AND** SHALL 重新抛出原始异常
