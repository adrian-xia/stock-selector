## ADDED Requirements

### Requirement: PBValueStrategy (PB低估值)
The system SHALL provide a `PBValueStrategy` in the strategy-implementations registry.

Default params: `{"pb_max": 2.0}`

Logic: `(pb > 0) AND (pb < pb_max)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("pb-value")` is called
- **THEN** it SHALL return a `PBValueStrategy` instance

### Requirement: PEGValueStrategy (PEG估值)
The system SHALL provide a `PEGValueStrategy` in the strategy-implementations registry.

Default params: `{"peg_max": 1.0}`

Logic: `(pe_ttm > 0) AND (profit_yoy > 0) AND (pe_ttm / profit_yoy < peg_max)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("peg-value")` is called
- **THEN** it SHALL return a `PEGValueStrategy` instance

### Requirement: PSValueStrategy (市销率低估值)
The system SHALL provide a `PSValueStrategy` in the strategy-implementations registry.

Default params: `{"ps_max": 3.0}`

Logic: `(ps_ttm > 0) AND (ps_ttm < ps_max)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("ps-value")` is called
- **THEN** it SHALL return a `PSValueStrategy` instance

### Requirement: GrossMarginUpStrategy (毛利率提升)
The system SHALL provide a `GrossMarginUpStrategy` in the strategy-implementations registry.

Default params: `{"gross_margin_min": 30.0}`

Logic: `(gross_margin >= gross_margin_min)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("gross-margin-up")` is called
- **THEN** it SHALL return a `GrossMarginUpStrategy` instance

### Requirement: CashflowQualityStrategy (现金流质量)
The system SHALL provide a `CashflowQualityStrategy` in the strategy-implementations registry.

Default params: `{"ocf_eps_ratio_min": 1.0}`

Logic: `(eps > 0) AND (ocf_per_share > 0) AND (ocf_per_share / eps >= ocf_eps_ratio_min)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("cashflow-quality")` is called
- **THEN** it SHALL return a `CashflowQualityStrategy` instance

### Requirement: ProfitContinuousGrowthStrategy (净利润连续增长)
The system SHALL provide a `ProfitContinuousGrowthStrategy` in the strategy-implementations registry.

Default params: `{"profit_growth_min": 5.0}`

Logic: `(profit_yoy >= profit_growth_min)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("profit-continuous-growth")` is called
- **THEN** it SHALL return a `ProfitContinuousGrowthStrategy` instance

### Requirement: CashflowCoverageStrategy (经营现金流覆盖)
The system SHALL provide a `CashflowCoverageStrategy` in the strategy-implementations registry.

Default params: `{"ocf_min": 0.5, "current_ratio_min": 1.0}`

Logic: `(ocf_per_share >= ocf_min) AND (current_ratio >= current_ratio_min)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("cashflow-coverage")` is called
- **THEN** it SHALL return a `CashflowCoverageStrategy` instance

### Requirement: QualityScoreStrategy (综合质量评分)
The system SHALL provide a `QualityScoreStrategy` in the strategy-implementations registry.

Default params: `{"score_min": 60.0}`

Logic: Multi-factor weighted scoring (ROE 30% + growth 25% + safety 25% + valuation 20%), total score >= score_min.

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("quality-score")` is called
- **THEN** it SHALL return a `QualityScoreStrategy` instance
