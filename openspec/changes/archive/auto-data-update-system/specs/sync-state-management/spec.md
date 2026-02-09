## ADDED Requirements

### Requirement: 任务状态存储

系统 SHALL 使用 Redis 存储同步任务的状态信息。

#### Scenario: 存储任务状态

- **WHEN** 设置任务状态为 "probing"
- **THEN** Redis 中存储 `sync_status:2026-02-10` = "probing"
- **AND** TTL 设置为 7 天

#### Scenario: 查询任务状态

- **WHEN** 查询任务状态
- **THEN** 从 Redis 读取 `sync_status:2026-02-10`
- **AND** 返回对应的状态值

#### Scenario: 状态自动过期

- **WHEN** 任务状态存储 7 天后
- **THEN** Redis 自动删除该状态记录

### Requirement: 状态流转

系统 SHALL 支持以下状态流转：pending → probing → syncing → completed 或 failed。

#### Scenario: 正常流转

- **WHEN** 任务从 pending 开始
- **AND** 依次流转为 probing → syncing → completed
- **THEN** 每次状态变更都记录到 Redis

#### Scenario: 超时失败

- **WHEN** 任务状态为 probing
- **AND** 超过超时时间仍无数据
- **THEN** 状态变更为 failed

#### Scenario: 同步失败

- **WHEN** 任务状态为 syncing
- **AND** 盘后链路执行失败
- **THEN** 状态变更为 failed

### Requirement: 嗅探计数

系统 SHALL 记录每个任务的嗅探次数。

#### Scenario: 递增嗅探计数

- **WHEN** 执行一次嗅探
- **THEN** Redis 中 `probe_count:2026-02-10` 递增 1

#### Scenario: 查询嗅探次数

- **WHEN** 查询嗅探次数
- **THEN** 从 Redis 读取 `probe_count:2026-02-10`
- **AND** 返回当前计数值

### Requirement: 嗅探任务 ID 存储

系统 SHALL 存储嗅探任务的 APScheduler 任务 ID，用于停止任务。

#### Scenario: 保存任务 ID

- **WHEN** 启动嗅探任务
- **THEN** 将任务 ID 存储到 Redis `probe_job_id:2026-02-10`

#### Scenario: 获取任务 ID

- **WHEN** 需要停止嗅探任务
- **THEN** 从 Redis 读取 `probe_job_id:2026-02-10`
- **AND** 使用该 ID 移除 APScheduler 任务

### Requirement: 避免重复执行

系统 SHALL 在执行任务前检查状态，避免重复执行。

#### Scenario: 任务已完成

- **WHEN** 任务状态为 completed
- **AND** 尝试再次执行任务
- **THEN** 跳过执行，记录日志

#### Scenario: 任务进行中

- **WHEN** 任务状态为 syncing
- **AND** 尝试再次执行任务
- **THEN** 跳过执行，记录日志
