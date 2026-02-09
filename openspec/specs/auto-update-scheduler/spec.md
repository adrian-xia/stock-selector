## ADDED Requirements

### Requirement: 每日自动触发

系统 SHALL 在每个交易日 15:30 自动触发数据更新任务。

#### Scenario: 交易日触发

- **WHEN** 当前日期为交易日
- **AND** 时间到达 15:30
- **THEN** 自动触发数据更新任务

#### Scenario: 非交易日跳过

- **WHEN** 当前日期为非交易日
- **AND** 时间到达 15:30
- **THEN** 记录日志并跳过执行

#### Scenario: 任务已完成跳过

- **WHEN** 当前日期为交易日
- **AND** 任务状态为 completed
- **THEN** 跳过执行，记录日志

### Requirement: 数据嗅探

系统 SHALL 在触发时先进行数据嗅探，检查数据是否就绪。

#### Scenario: 数据已就绪立即同步

- **WHEN** 15:30 触发任务
- **AND** 数据嗅探返回 True
- **THEN** 立即执行盘后链路
- **AND** 标记任务状态为 completed

#### Scenario: 数据未就绪启动嗅探任务

- **WHEN** 15:30 触发任务
- **AND** 数据嗅探返回 False
- **THEN** 启动定时嗅探任务（每 15 分钟一次）
- **AND** 标记任务状态为 probing

### Requirement: 定时嗅探任务

系统 SHALL 在数据未就绪时启动定时嗅探任务，每 15 分钟嗅探一次。

#### Scenario: 嗅探成功执行同步

- **WHEN** 嗅探任务触发
- **AND** 数据嗅探返回 True
- **THEN** 执行盘后链路
- **AND** 停止嗅探任务
- **AND** 标记任务状态为 completed

#### Scenario: 嗅探失败继续等待

- **WHEN** 嗅探任务触发
- **AND** 数据嗅探返回 False
- **THEN** 记录日志
- **AND** 继续等待下次嗅探

#### Scenario: 超时停止嗅探

- **WHEN** 嗅探任务触发
- **AND** 当前时间超过 18:00
- **THEN** 发送超时报警
- **AND** 停止嗅探任务
- **AND** 标记任务状态为 failed

### Requirement: 嗅探间隔配置

系统 SHALL 支持配置嗅探间隔时间。

#### Scenario: 使用默认间隔

- **WHEN** 未配置嗅探间隔
- **THEN** 使用默认值 15 分钟

#### Scenario: 使用自定义间隔

- **WHEN** 配置嗅探间隔为 10 分钟
- **THEN** 嗅探任务每 10 分钟触发一次

### Requirement: 超时时间配置

系统 SHALL 支持配置超时时间。

#### Scenario: 使用默认超时时间

- **WHEN** 未配置超时时间
- **THEN** 使用默认值 18:00

#### Scenario: 使用自定义超时时间

- **WHEN** 配置超时时间为 19:00
- **THEN** 在 19:00 之前持续嗅探

### Requirement: 复用盘后链路

系统 SHALL 复用现有的 `run_post_market_chain()` 函数执行数据同步。

#### Scenario: 调用盘后链路

- **WHEN** 数据就绪需要同步
- **THEN** 调用 `run_post_market_chain(target_date)`
- **AND** 执行完整的盘后链路流程

#### Scenario: 盘后链路失败

- **WHEN** 调用 `run_post_market_chain()` 失败
- **THEN** 记录错误日志
- **AND** 标记任务状态为 failed
- **AND** 发送报警通知
