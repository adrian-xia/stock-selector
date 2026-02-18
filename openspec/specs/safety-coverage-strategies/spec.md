## ADDED Requirements

### Requirement: 经营现金流覆盖策略
系统 SHALL 提供经营现金流覆盖策略（`cashflow-coverage`），筛选经营现金流能充分覆盖短期负债的股票。使用 ocf_per_share 与 current_ratio 组合判断。默认参数：`ocf_min=0.5`（每股经营现金流最低值），`current_ratio_min=1.0`（流动比率最低值）。

#### Scenario: 现金流覆盖充足
- **WHEN** 股票 ocf_per_share = 1.2，current_ratio = 1.8，阈值 ocf_min = 0.5，current_ratio_min = 1.0
- **THEN** 策略命中该股票

#### Scenario: 现金流不足
- **WHEN** 股票 ocf_per_share = 0.2，current_ratio = 1.5，阈值 ocf_min = 0.5
- **THEN** 策略不命中该股票

#### Scenario: 流动比率不足
- **WHEN** 股票 ocf_per_share = 1.0，current_ratio = 0.8，阈值 current_ratio_min = 1.0
- **THEN** 策略不命中该股票

#### Scenario: 数据缺失
- **WHEN** 股票 ocf_per_share 或 current_ratio 为 NaN
- **THEN** 策略不命中该股票
