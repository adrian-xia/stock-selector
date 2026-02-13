## MODIFIED Requirements

### Requirement: 系统应基于进度表检测数据完整性

系统 SHALL 通过 `stock_sync_progress` 表的 `data_date` 和 `indicator_date` 字段判断数据完整性，完成率 = `COUNT(data_date >= target AND indicator_date >= target) / COUNT(*)`。

#### Scenario: 检测需要同步的股票
- **WHEN** 目标日期为 2026-02-12，有 500 只股票的 data_date < 2026-02-12
- **THEN** 系统识别这 500 只股票需要同步数据

#### Scenario: 新股自动识别（data_date=1900-01-01）
- **WHEN** 新股加入进度表，data_date 为默认值 1900-01-01
- **THEN** 系统识别该股票需要从 data_start_date 开始同步全部历史数据

#### Scenario: 完成率计算（排除 delisted）
- **WHEN** 8000 只股票中 1000 只为 delisted，剩余 7000 只中 6650 只的 data_date >= target_date 且 indicator_date >= target_date
- **THEN** 系统计算完成率为 6650/7000 = 95%

#### Scenario: 完成率达标执行策略
- **WHEN** 完成率 97%（高于 95% 阈值）
- **THEN** 系统执行策略计算

#### Scenario: 完成率不达标跳过策略
- **WHEN** 完成率 92%（低于 95% 阈值）
- **THEN** 系统跳过策略计算，记录 WARNING 日志
