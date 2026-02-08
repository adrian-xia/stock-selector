## 1. 项目配置与模块骨架

- [x] 1.1 在 `pyproject.toml` 中添加 `apscheduler` 依赖，运行 `uv sync` 安装
- [x] 1.2 创建 `app/scheduler/` 目录结构：`__init__.py`、`core.py`、`jobs.py`、`cli.py`
- [x] 1.3 在 `app/config.py` 中添加调度器配置项：`scheduler_post_market_cron`（默认 `"30 15 * * 1-5"`）、`scheduler_stock_sync_cron`（默认 `"0 8 * * 6"`）

## 2. 调度器核心

- [x] 2.1 实现 `create_scheduler()`（`core.py`）：创建 `AsyncIOScheduler`，配置 MemoryJobStore、timezone=Asia/Shanghai、coalesce=True、max_instances=1、misfire_grace_time=300
- [x] 2.2 实现 `register_jobs(scheduler)`（`core.py`）：注册盘后链路 cron job 和周末股票列表同步 cron job，使用 `replace_existing=True`
- [x] 2.3 实现 `start_scheduler()` 和 `stop_scheduler()`（`core.py`）：供 FastAPI lifespan 调用
- [x] 2.4 在 `app/main.py` 的 lifespan 中集成调度器启动和停止

## 3. 盘后链路任务

- [x] 3.1 实现 `run_post_market_chain(target_date)`（`jobs.py`）：交易日校验 → sync → indicators → pipeline 串行执行，任一步骤失败中断并记录日志
- [x] 3.2 实现 `sync_daily_step(target_date)`（`jobs.py`）：查询所有上市股票，逐只调用 `DataManager.sync_daily()`，记录成功/失败数量
- [x] 3.3 实现 `indicator_step(target_date)`（`jobs.py`）：调用 `compute_incremental(session_factory, target_date)`
- [x] 3.4 实现 `pipeline_step(target_date)`（`jobs.py`）：获取全部策略名称，调用 `execute_pipeline()`，记录筛选结果

## 4. 周末维护任务

- [x] 4.1 实现 `sync_stock_list_job()`（`jobs.py`）：调用 `DataManager.sync_stock_list()`

## 5. CLI 命令

- [x] 5.1 实现 `run-chain` 命令（`cli.py`）：接受 `--date` 参数，手动触发完整盘后链路
- [x] 5.2 实现 `run-job` 命令（`cli.py`）：接受 `job_name` 和 `--date` 参数，手动触发单个步骤（sync-daily / indicators / pipeline / sync-stocks）
- [x] 5.3 在 `pyproject.toml` 中注册 CLI 入口点或确保 `python -m app.scheduler.cli` 可用

## 6. 单元测试

- [x] 6.1 编写 `tests/unit/test_scheduler_core.py`：测试 `create_scheduler()` 配置正确性（timezone、coalesce、max_instances）
- [x] 6.2 编写 `tests/unit/test_scheduler_jobs.py`：测试交易日校验逻辑、链路中断逻辑（mock DataManager 和 compute_incremental）
