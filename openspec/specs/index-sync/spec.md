## Requirements

### Requirement: 盘后链路指数数据同步
盘后链路 SHALL 在资金流向同步（步骤 3.5）之后、缓存刷新（步骤 4）之前，增加指数数据同步步骤（步骤 3.6）。该步骤调用 `sync_raw_index_daily` + `sync_raw_index_weight` + `sync_raw_index_technical` + `etl_index`。失败不阻断后续链路。

#### Scenario: 正常执行
- **WHEN** 盘后链路执行到指数数据同步步骤
- **THEN** 依次调用 sync_raw_index_daily、sync_raw_index_weight、sync_raw_index_technical、etl_index，记录日志

#### Scenario: 同步失败不阻断
- **WHEN** 指数数据同步步骤中任一方法抛出异常
- **THEN** 记录错误日志，继续执行后续步骤（缓存刷新、策略管道）
