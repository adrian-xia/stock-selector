## 1. 环境隔离配置

- [x] 1.1 修改 `app/config.py`：`env_file` 改为从 `APP_ENV_FILE` 环境变量读取，默认 `.env`
- [x] 1.2 修改 `alembic/env.py`：从 `app.config.settings` 读取数据库 URL，而非 `alembic.ini`
- [x] 1.3 创建 `.env.prod` 文件（生产环境配置模板）
- [x] 1.4 更新 `.env` 和 `.env.example`：添加新配置项说明
- [x] 1.5 验证环境隔离：`APP_ENV_FILE=.env.test` 时使用测试数据库

## 2. 数据模型

- [x] 2.1 在 `app/models/market.py` 中创建 `StockSyncProgress` 模型：ts_code(PK), data_date(DATE, default 1900-01-01), indicator_date(DATE, default 1900-01-01), status(VARCHAR, default 'idle', 枚举值: idle/syncing/computing/failed/delisted), retry_count(INTEGER, default 0), error_message(TEXT), updated_at(TIMESTAMP)
- [x] 2.2 在 `app/models/__init__.py` 中导出 `StockSyncProgress`
- [x] 2.3 创建 Alembic 迁移文件，生成 `stock_sync_progress` 表
- [x] 2.4 在 `Settings` 中添加新配置项：data_start_date, sync_stock_list_on_startup, batch_sync_max_retries, data_completeness_threshold, sync_batch_days, sync_batch_timeout, sync_failure_retry_cron, pipeline_completeness_deadline

## 3. 进度管理方法

- [x] 3.1 在 `app/data/manager.py` 中实现 `reset_stale_status()` 方法：将 `syncing`/`computing` 状态重置为 `idle`（进程崩溃恢复，重启时不可能还有正在处理的任务）
- [x] 3.2 在 `app/data/manager.py` 中实现 `init_sync_progress()` 方法：INSERT ... ON CONFLICT DO NOTHING，为所有未退市股票创建进度记录；随后调用 `sync_delisted_status()` 同步退市状态
- [x] 3.3 在 `app/data/manager.py` 中实现 `get_stocks_needing_sync(target_date)` 方法：查询 `status NOT IN ('delisted', 'failed') AND data_date < target_date` 的股票（failed 由 retry job 单独处理）
- [x] 3.4 在 `app/data/manager.py` 中实现 `get_stocks_needing_indicators(target_date)` 方法：查询 `status NOT IN ('delisted', 'failed') AND indicator_date < target_date AND data_date >= target_date` 的股票
- [x] 3.5 在 `app/data/manager.py` 中实现 `update_data_progress(ts_code, data_date)` 方法：更新 data_date
- [x] 3.6 在 `app/data/manager.py` 中实现 `update_indicator_progress(ts_code, indicator_date)` 方法：更新 indicator_date
- [x] 3.7 在 `app/data/manager.py` 中实现 `update_stock_status(ts_code, status, error_message=None)` 方法：更新 status 和 error_message
- [x] 3.8 在 `app/data/manager.py` 中实现 `get_sync_summary(target_date)` 方法：返回 {total, data_done, indicator_done, failed, completion_rate}，total 和 completion_rate 排除 status='delisted' 的股票
- [x] 3.9 在 `app/data/manager.py` 中实现 `get_failed_stocks(max_retries)` 方法：查询 `status='failed' AND retry_count < max_retries` 的股票
- [x] 3.10 编写单元测试验证进度管理方法

## 4. 同步流程锁

- [x] 4.1 在 `app/data/manager.py` 中实现 `acquire_sync_lock()` / `release_sync_lock()` 方法：使用 Redis SETNX 实现分布式锁（TTL 4 小时），防止启动流程、盘后链路、retry job 并发执行
- [x] 4.2 Redis 不可用时降级为无锁模式（记录 WARNING 日志），不阻断流程
- [x] 4.3 编写单元测试验证锁的获取、释放、超时自动释放

## 5. 批量数据拉取

- [x] 5.1 在 `app/data/manager.py` 中实现 `sync_stock_data_in_batches(code, start_date, end_date, batch_days=365)` 方法：按批次拉取数据，每批在事务中完成「批量写入日线数据 + 更新 data_date」，保证原子性
- [x] 5.2 实现失败处理：单批失败时事务回滚，标记 status='failed' + error_message + retry_count 不变，不影响其他股票
- [x] 5.3 改造 `batch_sync_daily()` 接口，增加可选的 `manager` 参数，避免每次调用都新建 BaoStockClient 和 DataManager
- [x] 5.4 编写单元测试验证批量拉取逻辑（多批次、断点续传、失败处理）

## 6. 批量指标计算

- [x] 6.1 在 `app/data/manager.py` 中实现 `compute_indicators_in_batches(code, start_date, end_date, batch_days=365, lookback_days=300)` 方法：按批次计算指标，每批在事务中完成「批量写入指标 + 更新 indicator_date」
- [x] 6.2 每批完成后在事务中更新 indicator_date，失败时事务回滚
- [x] 6.3 编写单元测试验证批量指标计算（lookback 窗口、多批次、失败处理）

## 7. 单只股票完整处理

- [x] 7.1 在 `app/data/manager.py` 中实现 `process_single_stock(ts_code, target_date)` 方法：数据拉取（按批次）→ 指标计算（按批次）→ 更新状态
- [x] 7.2 实现并发控制：使用 `asyncio.Semaphore` 限制同时处理的股票数
- [x] 7.3 实现 `process_stocks_batch(stocks, target_date, timeout)` 方法：带整体超时控制，超时后停止接受新任务，等待已启动的任务完成，记录超时日志
- [x] 7.4 编写单元测试验证单只股票完整处理流程

## 8. 启动流程改造

- [x] 8.1 在 `app/scheduler/core.py` 中实现 `sync_stock_list_on_startup()` 方法
- [x] 8.2 在 `app/scheduler/core.py` 中实现 `sync_from_progress()` 方法：获取同步锁 → reset_stale_status → 初始化进度表 → 查询待处理股票 → 批量处理 → 完成率日志 → 释放锁
- [x] 8.3 修改 `start_scheduler()` 方法：sync_stock_list_on_startup() → sync_from_progress() → 启动调度器
- [x] 8.4 验证断点续传：模拟中断后重启，确认只处理未完成的股票

## 9. 盘后链路改造

- [x] 9.1 修改 `run_post_market_chain()`：获取同步锁 → 更新股票列表 → reset_stale_status → 初始化进度 → 批量处理（带超时） → 完整性门控 → 策略执行/跳过 → 释放锁
- [x] 9.2 实现完整性门控：查询 get_sync_summary()，完成率 >= 阈值才执行策略
- [x] 9.3 实现 18:00 完整性告警：盘后链路完成时检查 failed 记录，超过截止时间则告警
- [x] 9.4 修改 `sync_daily_step()`：使用进度表驱动，过滤已完成的股票
- [x] 9.5 修改 `indicator_step()`：只处理 data_date >= target_date 且 indicator_date < target_date 的股票

## 10. 定时重试

- [x] 10.1 在 `app/scheduler/jobs.py` 中实现 `retry_failed_stocks_job()` 定时任务：获取同步锁 → 查询 `status='failed' AND retry_count < max_retries` → 从 data_date 恢复同步 → 每次重试 retry_count+1 → 释放锁
- [x] 10.2 超过 max_retries 的股票记录 WARNING 日志，不再自动重试
- [x] 10.3 重试后检查完整性，达到阈值则补跑策略
- [x] 10.4 在 `register_jobs()` 中注册 retry_failed_stocks_job，使用可配置的 cron 表达式
- [x] 10.5 编写单元测试验证定时重试逻辑（含重试次数上限）

## 11. 退市处理 + 智能过滤 + 连接池修复

- [x] 11.1 在 `app/data/manager.py` 中实现 `mark_stock_delisted(ts_code, delist_date)` 方法：使用事务同时更新 stocks 表（delist_date + list_status='D'）和 progress 表（status='delisted'）
- [x] 11.2 在 `app/data/manager.py` 中实现 `sync_delisted_status()` 方法：双向同步——正向标记新退市股票为 delisted，反向将取消退市的股票从 delisted 恢复为 idle
- [x] 11.3 在 `app/data/manager.py` 中实现 `should_have_data(stock, trade_date)` 方法：基于上市日期和退市日期判断（用于 init_sync_progress 初始过滤）
- [x] 11.4 在 BaoStockConnectionPool.acquire() 中使用 asyncio.Lock 保护 `_created_count` 的检查和递增
- [x] 11.5 编写单元测试验证退市事务处理（事务原子性、批量同步退市状态、反向恢复、筛选排除 delisted）

## 12. 日志和监控

- [x] 12.1 添加启动时更新股票列表的日志（成功/失败、耗时）
- [x] 12.2 添加进度表初始化的日志（总股票数、新增记录数、stale 状态重置数）
- [x] 12.3 添加批量处理的进度日志（已处理/总数、当前股票、当前批次）
- [x] 12.4 添加完整性门控的日志（完成率、阈值、是否执行策略）
- [x] 12.5 添加定时重试的日志（重试数量、成功数、失败数、达到上限数）
- [x] 12.6 添加同步锁的日志（获取/释放/获取失败）

## 13. 文档更新

- [x] 13.1 更新 README.md 说明新功能（环境隔离、累积进度模型、批量处理、断点续传）
- [x] 13.2 更新 CLAUDE.md 说明 V1 范围变更
- [x] 13.3 更新 docs/design/99-实施范围-V1与V2划分.md 标注为"✅ V1 已实施"
- [x] 13.4 更新 .env.example 添加新配置项说明

## 14. 测试和验证

- [x] 14.1 运行所有单元测试确保通过
- [x] 14.2 手动测试：首次启动，验证进度表初始化和批量同步
- [x] 14.3 手动测试：模拟中断后重启，验证断点续传（含 stale status 重置）
- [x] 14.4 手动测试：验证盘后链路完整性门控
- [x] 14.5 手动测试：验证定时重试功能（含重试次数上限）
- [x] 14.6 手动测试：验证环境隔离（APP_ENV_FILE=.env.test）
- [x] 14.7 手动测试：验证并发执行保护（同时触发两个同步流程，第二个应跳过）
