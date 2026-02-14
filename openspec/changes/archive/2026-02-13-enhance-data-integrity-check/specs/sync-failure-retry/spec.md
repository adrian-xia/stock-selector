## MODIFIED Requirements

### Requirement: 系统应通过累积进度表追踪每只股票的同步状态

系统 SHALL 维护 `stock_sync_progress` 表，每只股票一条记录，使用 `data_date` 和 `indicator_date` 追踪数据和指标分别同步到哪一天（累积模型，非每日重置）。status 字段支持 idle/syncing/computing/failed/delisted 五种状态。

#### Scenario: 初始化进度表（新股自动加入）
- **WHEN** 系统启动或盘后链路开始
- **THEN** 系统通过 INSERT ... ON CONFLICT DO NOTHING 为所有未退市股票创建进度记录，已有记录保持不变

#### Scenario: 新股的 data_date 默认为 1900-01-01
- **WHEN** 新股首次加入进度表
- **THEN** data_date 和 indicator_date 均为 1900-01-01，表示从未同步过

#### Scenario: 按批次更新 data_date（事务保证原子性）
- **WHEN** 某股票按 365 天/批拉取数据，第一批（2024-01-01 到 2024-12-31）完成
- **THEN** 系统在事务中同时完成批量写入日线数据和更新 data_date 为 2024-12-31

#### Scenario: 按批次更新 indicator_date（事务保证原子性）
- **WHEN** 某股票按 365 天/批计算指标，第一批完成
- **THEN** 系统在事务中同时完成批量写入指标和更新 indicator_date

#### Scenario: 断点续传
- **WHEN** 进程在处理第 3000 只股票时崩溃，重启后
- **THEN** 系统查询 status NOT IN ('delisted') AND data_date < target_date 的股票，只处理剩余未完成的股票

#### Scenario: 退市股票标记为 delisted
- **WHEN** 发现某股票已退市
- **THEN** 系统在事务中同时更新 stocks 表（delist_date + list_status='D'）和 progress 表（status='delisted'）

### Requirement: 系统应在盘后链路中做完整性门控

系统 SHALL 在盘后链路的批量处理完成后，检查完成率（排除 delisted 股票），只有达到阈值才执行策略。

#### Scenario: 完成率达标时执行策略
- **WHEN** 非 delisted 股票中，data_date >= target_date 且 indicator_date >= target_date 的占比 97%（高于 95% 阈值）
- **THEN** 系统执行策略计算

#### Scenario: 完成率不达标时跳过策略
- **WHEN** 完成率 92%（低于 95% 阈值）
- **THEN** 系统跳过策略计算，记录 WARNING 日志

#### Scenario: delisted 股票不计入完成率
- **WHEN** 8000 只股票中 1000 只为 delisted，剩余 7000 只中 6650 只完成
- **THEN** 完成率为 6650/7000 = 95%，而非 6650/8000 = 83%

### Requirement: 系统应定时重试失败的股票

系统 SHALL 通过定时任务（默认每天 20:00，盘后链路完成后）自动重试 status='failed' 的股票，从 data_date 恢复同步。

#### Scenario: 重试失败的股票
- **WHEN** 定时任务发现 3 只股票 status='failed'
- **THEN** 系统从各自的 data_date 恢复同步（数据拉取 + 指标计算）

#### Scenario: 重试后完整性达标则补跑策略
- **WHEN** 定时重试后完成率从 92% 提升到 97%（达到阈值）
- **THEN** 系统补跑策略计算

### Requirement: 系统应在 18:00 前检查数据完整性并告警

系统 SHALL 在盘后链路完成时检查进度表，如果仍有 failed 记录且当前时间已超过截止时间（默认 18:00），发送告警通知。

#### Scenario: 18:00 数据未齐全时告警
- **WHEN** 盘后链路完成，当前时间 18:15，仍有 50 只股票 status='failed'
- **THEN** 系统发送告警通知："{date} 仍有 50 只股票数据未齐全"

#### Scenario: 可配置截止时间
- **WHEN** 系统配置 PIPELINE_COMPLETENESS_DEADLINE="19:00"
- **THEN** 系统在 19:00 后才触发完整性告警

## ADDED Requirements

### Requirement: 系统应支持环境隔离

系统 SHALL 通过 APP_ENV_FILE 环境变量指定配置文件路径，实现生产/测试/开发环境的物理隔离。

#### Scenario: 生产环境使用独立数据库
- **WHEN** 设置 APP_ENV_FILE=.env.prod
- **THEN** 系统使用 .env.prod 中配置的数据库和 Redis

#### Scenario: 测试环境使用独立数据库
- **WHEN** 设置 APP_ENV_FILE=.env.test
- **THEN** 系统使用 .env.test 中配置的测试数据库和 Redis db

#### Scenario: 默认使用 .env
- **WHEN** 未设置 APP_ENV_FILE
- **THEN** 系统使用项目根目录的 .env 文件

### Requirement: 系统应支持批量数据处理

系统 SHALL 按 365 天/批拉取数据和计算指标，每批完成后更新进度。

#### Scenario: 按批次拉取数据
- **WHEN** 某股票需要从 2024-01-01 同步到 2026-02-12
- **THEN** 系统分 3 批处理：2024-01-01~2024-12-31、2025-01-01~2025-12-31、2026-01-01~2026-02-12

#### Scenario: 按批次计算指标（含 lookback 窗口）
- **WHEN** 某股票需要计算 2024-01-01 到 2024-12-31 的指标
- **THEN** 系统加载 2023-03-07（2024-01-01 - 300天）到 2024-12-31 的数据，计算指标

#### Scenario: 每批更新进度
- **WHEN** 第一批数据（2024-01-01~2024-12-31）拉取完成
- **THEN** 系统在事务中将 data_date 更新为 2024-12-31，即使后续批次失败也不会丢失已完成的进度
