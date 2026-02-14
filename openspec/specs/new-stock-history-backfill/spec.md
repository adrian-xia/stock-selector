## MODIFIED Requirements

### Requirement: 新股通过累积进度模型自动补齐历史数据

系统 SHALL 在 init_sync_progress() 中为新股创建 data_date=1900-01-01 的记录，后续批量处理流程自动从 data_start_date 开始补齐历史数据。

#### Scenario: 新股自动加入进度表
- **WHEN** 股票列表更新后发现新股
- **THEN** init_sync_progress() 为新股创建记录，data_date=1900-01-01

#### Scenario: 新股从 data_start_date 开始同步
- **WHEN** 某新股 data_date=1900-01-01，data_start_date=2024-01-01
- **THEN** 系统从 2024-01-01 开始按 365 天/批同步历史数据

#### Scenario: 新股按批次同步不阻断其他股票
- **WHEN** 某新股需要同步 2 年历史数据（2 批）
- **THEN** 系统按批次处理，每批完成后更新 data_date，不影响其他股票的处理

### Requirement: 系统应记录新股历史数据补齐的统计信息

系统 SHALL 记录新股历史数据补齐的统计信息。

#### Scenario: 记录补齐统计信息
- **WHEN** 系统处理 10 只新股，其中 8 只成功，2 只失败
- **THEN** 系统记录统计信息：total=10, success=8, failed=2
