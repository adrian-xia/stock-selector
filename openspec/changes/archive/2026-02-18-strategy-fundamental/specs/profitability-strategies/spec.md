## ADDED Requirements

### Requirement: 毛利率提升策略
系统 SHALL 提供毛利率提升策略（`gross-margin-up`），筛选毛利率高于阈值的股票。默认参数：`gross_margin_min=30.0`。

#### Scenario: 毛利率高于阈值
- **WHEN** 股票 gross_margin = 45.0%，阈值 gross_margin_min = 30.0
- **THEN** 策略命中该股票

#### Scenario: 毛利率低于阈值
- **WHEN** 股票 gross_margin = 20.0%，阈值 gross_margin_min = 30.0
- **THEN** 策略不命中该股票

#### Scenario: 毛利率数据缺失
- **WHEN** 股票 gross_margin 为 NaN
- **THEN** 策略不命中该股票

### Requirement: 现金流质量策略
系统 SHALL 提供现金流质量策略（`cashflow-quality`），筛选每股经营现金流大于每股收益的股票。默认参数：`ocf_eps_ratio_min=1.0`。两个字段必须有效（非 NaN）。

#### Scenario: 现金流质量好
- **WHEN** 股票 ocf_per_share = 2.5，eps = 1.8，ratio = 1.39，阈值 ocf_eps_ratio_min = 1.0
- **THEN** 策略命中该股票

#### Scenario: 现金流质量差
- **WHEN** 股票 ocf_per_share = 0.5，eps = 1.8，ratio = 0.28
- **THEN** 策略不命中该股票

#### Scenario: EPS 为负
- **WHEN** 股票 eps = -0.5（亏损）
- **THEN** 策略不命中该股票

#### Scenario: 数据缺失
- **WHEN** 股票 ocf_per_share 为 NaN
- **THEN** 策略不命中该股票

### Requirement: 净利润连续增长策略
系统 SHALL 提供净利润连续增长策略（`profit-continuous-growth`），筛选利润同比增长率持续为正的股票。默认参数：`profit_growth_min=5.0`（最低增长率阈值）。

#### Scenario: 利润增长超过阈值
- **WHEN** 股票 profit_yoy = 15.0%，阈值 profit_growth_min = 5.0
- **THEN** 策略命中该股票

#### Scenario: 利润增长低于阈值
- **WHEN** 股票 profit_yoy = 3.0%，阈值 profit_growth_min = 5.0
- **THEN** 策略不命中该股票

#### Scenario: 利润负增长
- **WHEN** 股票 profit_yoy = -10.0%
- **THEN** 策略不命中该股票
