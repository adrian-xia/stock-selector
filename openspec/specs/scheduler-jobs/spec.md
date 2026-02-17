## MODIFIED Requirements

### Requirement: _build_manager 使用 TushareClient
_build_manager() SHALL 创建 TushareClient 实例替代 BaoStockClient + AKShareClient，不再需要 BaoStock 连接池。

#### Scenario: 构建 DataManager
- **WHEN** 调用 _build_manager()
- **THEN** 返回使用 TushareClient 的 DataManager 实例，primary="tushare"

### Requirement: 盘后链路适配按日期同步
run_post_market_chain SHALL 使用按日期全市场同步模式：sync_raw_daily(target) → etl_daily(target)，替代原有的逐只股票 process_stocks_batch。在批量数据拉取（步骤 3）之后、缓存刷新（步骤 4）之前，增加资金流向同步步骤（步骤 3.5）。该步骤调用 sync_raw_moneyflow + sync_raw_top_list + etl_moneyflow。失败不阻断后续链路。

#### Scenario: 盘后链路执行
- **WHEN** 盘后链路触发（交易日 15:30）
- **THEN** 执行：交易日历 → 股票列表 → 批量数据拉取 → **资金流向同步** → 缓存刷新 → 完整性门控 → 策略

#### Scenario: 同步性能提升
- **WHEN** 盘后链路执行全市场日线同步
- **THEN** 仅需 3-4 次 API 调用（vs 旧方案 ~5000 次），耗时从数十分钟降至数秒

#### Scenario: 资金流向同步失败不阻断
- **WHEN** 资金流向同步步骤抛出异常
- **THEN** 记录错误日志，继续执行缓存刷新和策略管道
