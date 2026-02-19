## REMOVED Requirements

### Requirement: BaoStock 客户端
**Reason**: 完全替换为 TushareClient，BaoStock 接口不稳定
**Migration**: 使用 TushareClient 替代，实现相同的 DataSourceClient Protocol

### Requirement: AKShare 客户端
**Reason**: 完全替换为 TushareClient，AKShare 接口不稳定
**Migration**: 使用 TushareClient 替代，不再需要备用数据源

## MODIFIED Requirements

### Requirement: DataSourceClient Protocol 实现
系统 SHALL 提供 TushareClient 作为 DataSourceClient Protocol 的唯一实现。

#### Scenario: TushareClient 满足 Protocol
- **WHEN** 检查 TushareClient 是否实现 DataSourceClient Protocol
- **THEN** isinstance(TushareClient(), DataSourceClient) 返回 True
