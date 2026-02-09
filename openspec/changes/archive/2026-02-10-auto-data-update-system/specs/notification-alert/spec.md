## ADDED Requirements

### Requirement: 通知接口

系统 SHALL 提供统一的通知接口，支持不同级别的报警。

#### Scenario: 发送 ERROR 级别通知

- **WHEN** 调用 `send(level=ERROR, title="数据同步失败", message="...")`
- **THEN** 记录 ERROR 级别日志

#### Scenario: 发送 WARNING 级别通知

- **WHEN** 调用 `send(level=WARNING, title="数据嗅探超时", message="...")`
- **THEN** 记录 WARNING 级别日志

#### Scenario: 发送 INFO 级别通知

- **WHEN** 调用 `send(level=INFO, title="数据同步成功", message="...")`
- **THEN** 记录 INFO 级别日志

### Requirement: 通知元数据

系统 SHALL 支持在通知中附加元数据。

#### Scenario: 附加元数据

- **WHEN** 调用 `send(..., metadata={"date": "2026-02-10", "probe_count": 3})`
- **THEN** 日志中包含元数据信息

### Requirement: V1 暂存实现

系统 SHALL 在 V1 阶段仅记录日志，不接入实际通知服务。

#### Scenario: V1 日志记录

- **WHEN** 发送通知
- **THEN** 仅记录日志，不调用外部服务

#### Scenario: 预留接口

- **WHEN** V2 需要接入企业微信
- **THEN** 可以在 `send()` 方法中增加企业微信调用逻辑
- **AND** 不需要修改调用方代码

### Requirement: 超时报警

系统 SHALL 在数据嗅探超时时发送报警通知。

#### Scenario: 超时报警

- **WHEN** 当前时间超过 18:00
- **AND** 数据仍未就绪
- **THEN** 发送 ERROR 级别通知
- **AND** 标题为 "数据同步超时"
- **AND** 消息包含日期、嗅探次数等信息

### Requirement: 同步失败报警

系统 SHALL 在盘后链路执行失败时发送报警通知。

#### Scenario: 同步失败报警

- **WHEN** 盘后链路执行失败
- **THEN** 发送 ERROR 级别通知
- **AND** 标题为 "数据同步失败"
- **AND** 消息包含错误信息
