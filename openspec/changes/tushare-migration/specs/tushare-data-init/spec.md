## ADDED Requirements

### Requirement: Tushare 全量数据初始化 CLI
系统 SHALL 提供基于 Tushare 的全量数据初始化命令，支持从指定起始日期拉取全部历史数据。

#### Scenario: 执行全量初始化
- **WHEN** 运行 `uv run python -m app.data.cli init-tushare --start-date 2024-01-01`
- **THEN** 按顺序执行：stock_basic → trade_cal → 逐交易日(daily+adj_factor+daily_basic) → fina_indicator → moneyflow → 指数/板块 → 技术指标计算

#### Scenario: 断点续传
- **WHEN** 初始化过程中断后重新执行
- **THEN** 从上次中断的位置继续，不重复拉取已完成的数据

### Requirement: 初始化进度追踪
系统 SHALL 使用 `raw_sync_progress` 表追踪原始数据拉取进度，记录每个接口每个日期的完成状态。

#### Scenario: 查看初始化进度
- **WHEN** 初始化过程中查看进度
- **THEN** 显示已完成/总计交易日数、当前正在处理的日期、预计剩余时间

### Requirement: 初始化起始日期可配置
系统 SHALL 支持通过 `DATA_START_DATE` 配置项控制历史数据起始日期，测试环境默认 2024-01-01，生产环境可配置为 2006-01-01。

#### Scenario: 测试环境初始化
- **WHEN** DATA_START_DATE=2024-01-01
- **THEN** 从 2024-01-01 开始拉取历史数据

#### Scenario: 生产环境初始化
- **WHEN** DATA_START_DATE=2006-01-01
- **THEN** 从 2006-01-01 开始拉取历史数据（约 5000 个交易日）

### Requirement: 初始化性能要求
全量初始化 SHALL 在合理时间内完成：测试环境（2024 起）30 分钟内，生产环境（2006 起）2 小时内。

#### Scenario: 测试环境初始化耗时
- **WHEN** 从 2024-01-01 初始化到当前日期（约 500 个交易日）
- **THEN** 总耗时不超过 30 分钟
