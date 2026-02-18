## ADDED Requirements

### Requirement: PB 低估值策略
系统 SHALL 提供 PB 低估值策略（`pb-value`），筛选市净率低于阈值的股票。默认参数：`pb_max=2.0`。PB 必须大于 0（排除负净资产）。

#### Scenario: PB 低于阈值且为正值
- **WHEN** 股票 PB = 1.5，阈值 pb_max = 2.0
- **THEN** 策略命中该股票

#### Scenario: PB 超过阈值
- **WHEN** 股票 PB = 3.0，阈值 pb_max = 2.0
- **THEN** 策略不命中该股票

#### Scenario: PB 为负值
- **WHEN** 股票 PB = -0.5（净资产为负）
- **THEN** 策略不命中该股票

#### Scenario: PB 数据缺失
- **WHEN** 股票 PB 为 NaN
- **THEN** 策略不命中该股票

### Requirement: PEG 估值策略
系统 SHALL 提供 PEG 估值策略（`peg-value`），筛选 PEG < 阈值的股票。PEG = PE_TTM / profit_yoy。默认参数：`peg_max=1.0`。PE_TTM 和 profit_yoy 必须大于 0。

#### Scenario: PEG 低于阈值
- **WHEN** 股票 PE_TTM = 15，profit_yoy = 25%，PEG = 0.6，阈值 peg_max = 1.0
- **THEN** 策略命中该股票

#### Scenario: PEG 超过阈值
- **WHEN** 股票 PE_TTM = 30，profit_yoy = 10%，PEG = 3.0，阈值 peg_max = 1.0
- **THEN** 策略不命中该股票

#### Scenario: 利润负增长
- **WHEN** 股票 profit_yoy = -10%
- **THEN** 策略不命中该股票（PEG 无意义）

#### Scenario: PE 为负
- **WHEN** 股票 PE_TTM = -5（亏损）
- **THEN** 策略不命中该股票

### Requirement: 市销率低估值策略
系统 SHALL 提供市销率低估值策略（`ps-value`），筛选 PS_TTM 低于阈值的股票。默认参数：`ps_max=3.0`。PS_TTM 必须大于 0。

#### Scenario: PS 低于阈值
- **WHEN** 股票 PS_TTM = 2.0，阈值 ps_max = 3.0
- **THEN** 策略命中该股票

#### Scenario: PS 超过阈值
- **WHEN** 股票 PS_TTM = 5.0，阈值 ps_max = 3.0
- **THEN** 策略不命中该股票

#### Scenario: PS 数据缺失
- **WHEN** 股票 PS_TTM 为 NaN
- **THEN** 策略不命中该股票
