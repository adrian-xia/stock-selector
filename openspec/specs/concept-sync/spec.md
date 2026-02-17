## ADDED Requirements

### Requirement: 盘后链路板块数据同步
盘后链路 SHALL 在指数数据同步（步骤 3.6）之后、缓存刷新（步骤 4）之前，增加板块数据同步步骤（步骤 3.7）。该步骤调用已有的 `sync_concept_daily` 同步同花顺板块日线行情，然后调用 `update_concept_indicators` 计算板块技术指标。失败不阻断后续链路。

#### Scenario: 正常执行
- **WHEN** 盘后链路执行到板块数据同步步骤
- **THEN** 调用 sync_concept_daily 同步当日板块日线行情，调用 update_concept_indicators 计算技术指标，记录日志

#### Scenario: 同步失败不阻断
- **WHEN** 板块数据同步步骤中任一方法抛出异常
- **THEN** 记录错误日志，继续执行后续步骤（缓存刷新、策略管道）
