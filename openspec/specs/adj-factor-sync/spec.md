## REMOVED Requirements

### Requirement: Adj factor data retrieval from BaoStock
**Reason**: BaoStock 数据源已移除，复权因子通过 Tushare adj_factor 接口获取
**Migration**: DataManager.sync_raw_daily 已包含 adj_factor 同步，无需独立的 BaoStock 复权因子获取

### Requirement: Batch update adj_factor in stock_daily
**Reason**: 复权因子已通过 ETL 流程自动写入 stock_daily，无需独立的批量更新
**Migration**: etl_daily 从 raw_tushare_adj_factor 表 JOIN 清洗后写入 stock_daily

### Requirement: Full adj factor import CLI command
**Reason**: BaoStock 数据源已移除，独立的 adj factor CLI 命令不再需要
**Migration**: 复权因子通过 sync_raw_daily + etl_daily 流程自动处理

### Requirement: Incremental adj factor sync
**Reason**: 已集成到 DataManager 的按日期同步流程中
**Migration**: sync_raw_daily 每次同步自动包含 adj_factor 数据
