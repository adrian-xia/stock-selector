## MODIFIED Requirements

### Requirement: 批量同步改为按日期模式
batch_sync_daily SHALL 改为按日期批量同步模式：给定一组交易日期，逐日调用 sync_raw_daily + etl_daily，替代原有的逐只股票同步模式。

#### Scenario: 批量同步多个交易日
- **WHEN** 调用 batch_sync_daily(trade_dates=[date(2026,2,13), date(2026,2,14)])
- **THEN** 逐日执行 sync_raw_daily + etl_daily，每日仅 3-4 次 API 调用

#### Scenario: 使用 TushareClient 限流
- **WHEN** 调用 batch_sync_daily
- **THEN** 使用 TushareClient 的令牌桶限流，无需连接池参数

## REMOVED Requirements

### Requirement: BaoStock 连接池参数
**Reason**: BaoStock 已移除，不再需要连接池
**Migration**: TushareClient 使用无状态 HTTP API，通过令牌桶限流
