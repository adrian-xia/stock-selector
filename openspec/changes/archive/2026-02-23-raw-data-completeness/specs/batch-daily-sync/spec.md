## MODIFIED Requirements

### Requirement: process_stocks_batch raw-first 路径
process_stocks_batch 和 process_single_stock SHALL 通过 raw 表中转写入业务表，不再直接写入 stock_daily。

#### Scenario: 批量处理走 raw-first
- **WHEN** 盘后链路或启动同步调用 process_stocks_batch
- **THEN** 每只股票的数据先写入 raw_tushare_daily/adj_factor/daily_basic，再通过 etl_daily 清洗到 stock_daily

#### Scenario: 失败重试走 raw-first
- **WHEN** retry_failed_stocks_job 重试失败股票
- **THEN** 重试逻辑同样走 raw-first 路径，与正常同步路径一致

#### Scenario: stock_sync_progress 更新不变
- **WHEN** 单只股票 raw 同步 + ETL 完成
- **THEN** stock_sync_progress 的 data_date 和 indicator_date 更新逻辑保持不变
