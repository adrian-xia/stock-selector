## REMOVED Requirements

### Requirement: BaoStock 连接池
**Reason**: BaoStock 数据源已完全移除，连接池不再需要
**Migration**: TushareClient 使用无状态 HTTP API，通过令牌桶限流控制请求频率，无需连接池
