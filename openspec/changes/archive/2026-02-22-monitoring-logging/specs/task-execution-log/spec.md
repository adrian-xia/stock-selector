## ADDED Requirements

### Requirement: 任务执行日志表
系统 SHALL 提供 `task_execution_log` 数据库表，记录调度任务的执行历史。

字段：
- `id`: 自增主键
- `task_name`: VARCHAR(100)，任务名称（如 "post_market_pipeline", "sync_raw_daily"）
- `status`: VARCHAR(20)，执行状态（running / success / failed）
- `started_at`: TIMESTAMP，开始时间
- `finished_at`: TIMESTAMP，结束时间（nullable，running 时为空）
- `duration_seconds`: DECIMAL(10,2)，执行耗时（nullable）
- `result_summary`: JSONB，执行结果摘要（nullable）
- `error_message`: TEXT，错误信息（nullable，仅 failed 时有值）
- `trade_date`: DATE，关联交易日（nullable）

索引：
- `idx_task_log_name_started` ON (task_name, started_at DESC)
- `idx_task_log_status` ON (status)
- `idx_task_log_trade_date` ON (trade_date)

#### Scenario: 表结构创建
- **WHEN** 执行 `alembic upgrade head`
- **THEN** `task_execution_log` 表 SHALL 被创建，包含上述所有字段和索引

### Requirement: 任务执行日志写入
系统 SHALL 提供 `TaskLogger` 类，用于记录任务执行的开始和结束。

#### Scenario: 记录任务开始
- **WHEN** 调用 `task_logger.start(task_name="post_market_pipeline", trade_date=date(2026,2,22))`
- **THEN** SHALL 向 task_execution_log 插入一条 status="running" 的记录
- **AND** SHALL 返回记录 ID 用于后续更新

#### Scenario: 记录任务成功
- **WHEN** 调用 `task_logger.finish(log_id, status="success", result_summary={...})`
- **THEN** SHALL 更新对应记录的 status="success"、finished_at、duration_seconds、result_summary

#### Scenario: 记录任务失败
- **WHEN** 调用 `task_logger.finish(log_id, status="failed", error_message="...")`
- **THEN** SHALL 更新对应记录的 status="failed"、finished_at、duration_seconds、error_message

### Requirement: 任务执行日志上下文管理器
系统 SHALL 提供 `task_logger.track(task_name, trade_date)` 异步上下文管理器，自动记录任务的开始、成功和失败。

#### Scenario: 任务成功时自动记录
- **WHEN** 使用 `async with task_logger.track("sync_raw_daily", trade_date):`
- **THEN** 进入时 SHALL 记录 running，正常退出时 SHALL 记录 success

#### Scenario: 任务异常时自动记录失败
- **WHEN** 使用 `async with task_logger.track(...)` 且内部抛出异常
- **THEN** SHALL 记录 failed 和 error_message
- **AND** SHALL 重新抛出原始异常

### Requirement: 任务执行日志查询 API
系统 SHALL 提供 `GET /api/v1/tasks/logs` 端点，查询任务执行历史。

查询参数：
- `task_name`: 按任务名过滤（可选）
- `status`: 按状态过滤（可选）
- `trade_date`: 按交易日过滤（可选）
- `limit`: 返回条数（默认 50，最大 200）
- `offset`: 分页偏移（默认 0）

#### Scenario: 查询全部任务日志
- **WHEN** 调用 `GET /api/v1/tasks/logs`
- **THEN** SHALL 返回最近 50 条任务执行记录，按 started_at DESC 排序

#### Scenario: 按任务名过滤
- **WHEN** 调用 `GET /api/v1/tasks/logs?task_name=post_market_pipeline`
- **THEN** SHALL 仅返回 task_name="post_market_pipeline" 的记录

#### Scenario: 按交易日过滤
- **WHEN** 调用 `GET /api/v1/tasks/logs?trade_date=2026-02-22`
- **THEN** SHALL 仅返回 trade_date=2026-02-22 的记录
