## ADDED Requirements

### Requirement: Tushare 配置项
系统 SHALL 支持以下 Tushare 配置项：tushare_token, tushare_retry_count, tushare_retry_interval, tushare_qps_limit, tushare_batch_size。

#### Scenario: 通过环境变量配置 token
- **WHEN** .env 文件包含 TUSHARE_TOKEN=xxx
- **THEN** settings.tushare_token 为 "xxx"

#### Scenario: 默认限流配置
- **WHEN** 未配置 tushare_qps_limit
- **THEN** 默认值为 400（次/分钟）

## REMOVED Requirements

### Requirement: BaoStock 配置项
**Reason**: BaoStock 数据源已移除
**Migration**: 使用 tushare_* 配置项替代

### Requirement: AKShare 配置项
**Reason**: AKShare 数据源已移除
**Migration**: 使用 tushare_* 配置项替代
