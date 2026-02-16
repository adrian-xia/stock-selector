## MODIFIED Requirements

### Requirement: _build_manager 使用 TushareClient
_build_manager() SHALL 创建 TushareClient 实例替代 BaoStockClient + AKShareClient，不再需要 BaoStock 连接池。

#### Scenario: 构建 DataManager
- **WHEN** 调用 _build_manager()
- **THEN** 返回使用 TushareClient 的 DataManager 实例，primary="tushare"

### Requirement: 盘后链路适配按日期同步
run_post_market_chain SHALL 使用按日期全市场同步模式：sync_raw_daily(target) → etl_daily(target)，替代原有的逐只股票 process_stocks_batch。

#### Scenario: 盘后链路执行
- **WHEN** 盘后链路触发（交易日 15:30）
- **THEN** 执行：交易日历 → 股票列表 → sync_raw_daily → etl_daily → 指标计算 → 缓存刷新 → 完整性门控 → 策略

#### Scenario: 同步性能提升
- **WHEN** 盘后链路执行全市场日线同步
- **THEN** 仅需 3-4 次 API 调用（vs 旧方案 ~5000 次），耗时从数十分钟降至数秒
