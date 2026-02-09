## MODIFIED Requirements

### Requirement: 调度器任务注册

系统 SHALL 注册自动数据更新任务，替换原有的盘后链路任务。

#### Scenario: 注册自动更新任务

- **WHEN** 调度器启动
- **THEN** 注册 `auto_update_job` 任务
- **AND** 触发时间为每日 15:30
- **AND** 任务 ID 为 "auto_data_update"
- **AND** 任务名称为 "自动数据更新"

#### Scenario: 移除原有盘后链路任务

- **WHEN** 调度器启动
- **THEN** 不再注册 `post_market_chain` 任务
- **AND** 原有的 `run_post_market_chain()` 函数保留供调用

#### Scenario: 保留周末任务

- **WHEN** 调度器启动
- **THEN** 仍然注册 `stock_list_sync` 任务
- **AND** 触发时间为每周六 08:00

## ADDED Requirements

### Requirement: 自动更新任务配置

系统 SHALL 支持通过配置项控制自动更新任务的行为。

#### Scenario: 启用自动更新

- **WHEN** 配置 `AUTO_UPDATE_ENABLED=true`
- **THEN** 注册自动更新任务

#### Scenario: 禁用自动更新

- **WHEN** 配置 `AUTO_UPDATE_ENABLED=false`
- **THEN** 不注册自动更新任务
- **AND** 记录日志说明已禁用

#### Scenario: 自定义触发时间

- **WHEN** 配置 `SCHEDULER_AUTO_UPDATE_CRON="30 16 * * 1-5"`
- **THEN** 自动更新任务在每日 16:30 触发
