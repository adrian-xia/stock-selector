## MODIFIED Requirements

### Requirement: 盘后链路适配按日期同步
run_post_market_chain SHALL 在批量数据拉取（步骤 3）之后、缓存刷新（步骤 4）之前，增加资金流向同步步骤（步骤 3.5）。该步骤调用 sync_raw_moneyflow + sync_raw_top_list + etl_moneyflow。失败不阻断后续链路。

#### Scenario: 盘后链路执行
- **WHEN** 盘后链路触发（交易日 15:30）
- **THEN** 执行：交易日历 → 股票列表 → 批量数据拉取 → **资金流向同步** → 缓存刷新 → 完整性门控 → 策略

#### Scenario: 资金流向同步失败不阻断
- **WHEN** 资金流向同步步骤抛出异常
- **THEN** 记录错误日志，继续执行缓存刷新和策略管道
