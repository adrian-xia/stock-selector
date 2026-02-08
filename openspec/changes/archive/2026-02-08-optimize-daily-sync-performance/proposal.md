## Why

Phase 5 定时任务验证发现日线同步性能严重瓶颈：每只股票都要执行 `login()` → `query()` → `logout()` 循环，导致 8000+ 只股票的完整同步预计需要 2-3 小时。这使得盘后数据更新链路无法在合理时间内完成，影响次日选股的数据时效性。

## What Changes

- 实现 BaoStock 连接池管理，复用登录会话，避免每只股票都重新登录
- 支持批量查询多只股票的日线数据，减少网络往返次数
- 添加并发控制，在不触发限流的前提下并行下载数据
- 优化日线同步步骤的执行策略，从串行逐只改为批量并发
- 保持现有 API 接口不变，优化仅在内部实现层

## Capabilities

### New Capabilities
- `baostock-connection-pool`: BaoStock 连接池管理，支持会话复用和生命周期管理
- `batch-daily-sync`: 批量日线数据同步，支持分批查询和并发下载

### Modified Capabilities
- `data-source-clients`: 修改 BaoStockClient 的内部实现，支持连接池和批量查询，但保持公共接口不变
- `scheduler-jobs`: 修改 `sync_daily_step()` 的实现策略，从逐只串行改为批量并发

## Impact

**受影响的代码：**
- `app/data/baostock.py` — BaoStockClient 内部实现重构
- `app/scheduler/jobs.py` — sync_daily_step() 执行策略优化

**受影响的配置：**
- `.env` — 新增批量大小、并发数等配置项

**性能预期：**
- 日线同步时间从 2-3 小时降低到 15-30 分钟（预期提升 4-8 倍）

**兼容性：**
- 公共 API 接口保持不变，现有调用代码无需修改
- 数据库 schema 无变化
- 测试用例可能需要更新 mock 逻辑
