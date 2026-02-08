## Why

数据采集、技术指标计算、策略管道已全部实现，但目前只能通过 CLI 命令手动触发。系统缺少自动化编排能力，无法在每个交易日盘后自动完成"日线同步 → 技术指标计算 → 策略管道执行"的完整链路。定时任务调度是让系统从"能用"变为"自动运转"的关键模块。

## What Changes

- 新增 `app/scheduler/` 模块，基于 APScheduler 实现进程内定时任务调度
- 新增盘后核心链路：交易日校验 → 日线增量同步 → 技术指标增量计算 → 策略管道执行
- 新增周末维护任务：股票列表全量同步
- 新增 CLI 命令支持手动触发任务链和单个任务
- 新增调度器配置项到 `app/config.py`
- V1 简化：去掉 Redis 分布式锁、DAG 引擎、执行日志表、Telegram/邮件告警、HTTP 管理 API；任务链为线性串行执行；失败只写日志；APScheduler 用 SQLite Job Store

## Capabilities

### New Capabilities
- `scheduler-core`: APScheduler 调度器配置、启动/停止生命周期管理、任务注册
- `scheduler-jobs`: 盘后核心链路任务定义（日线同步、技术指标、策略管道）、周末维护任务、交易日校验逻辑
- `scheduler-cli`: CLI 命令手动触发任务链或单个任务（run-chain / run-job）

### Modified Capabilities
（无——调度器是全新模块，不修改现有 spec 的需求定义）

## Impact

- **新增目录：** `app/scheduler/`（core.py、jobs.py、cli.py）
- **修改文件：** `app/config.py`（新增调度器配置项）、`app/main.py`（lifespan 中启动/停止调度器）
- **依赖模块：** 消费 `DataManager.sync_daily()`、`DataManager.is_trade_day()`、`compute_incremental()`、`execute_pipeline()`
- **第三方依赖：** APScheduler（需添加到 pyproject.toml）
- **存储：** APScheduler 使用 SQLite 文件作为 Job Store（`data/scheduler.db`），不新增 PostgreSQL 表
