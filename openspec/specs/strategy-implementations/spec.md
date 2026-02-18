## MODIFIED Requirements

### Requirement: DonchianBreakoutStrategy (唐奇安通道突破)
The system SHALL provide a `DonchianBreakoutStrategy` in the strategy-implementations registry.

Default params: `{"period": 20}`

Logic: `(prev_close <= prev_donchian_upper) AND (close > donchian_upper) AND (vol > 0)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("donchian-breakout")` is called
- **THEN** it SHALL return a `DonchianBreakoutStrategy` instance

### Requirement: ATRBreakoutStrategy (ATR波动率突破)
The system SHALL provide an `ATRBreakoutStrategy` in the strategy-implementations registry.

Default params: `{"atr_multiplier": 1.5}`

Logic: `(close > ma20 + atr14 * atr_multiplier) AND (prev_close <= prev_ma20 + prev_atr14 * atr_multiplier) AND (vol > 0)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("atr-breakout")` is called
- **THEN** it SHALL return an `ATRBreakoutStrategy` instance

### Requirement: CCIOverboughtOversoldStrategy (CCI超买超卖)
The system SHALL provide a `CCIOverboughtOversoldStrategy` in the strategy-implementations registry.

Default params: `{"oversold": -100, "bounce": -80}`

Logic: `(prev_cci <= oversold) AND (cci > bounce) AND (vol > 0)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("cci-oversold")` is called
- **THEN** it SHALL return a `CCIOverboughtOversoldStrategy` instance

### Requirement: WilliamsRStrategy (Williams %R 超卖反弹)
The system SHALL provide a `WilliamsRStrategy` in the strategy-implementations registry.

Default params: `{"oversold": -80, "bounce": -50}`

Logic: `(prev_wr <= oversold) AND (wr > bounce) AND (vol > 0)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("williams-r")` is called
- **THEN** it SHALL return a `WilliamsRStrategy` instance

### Requirement: BIASStrategy (BIAS乖离率)
The system SHALL provide a `BIASStrategy` in the strategy-implementations registry.

Default params: `{"oversold_bias": -6.0}`

Logic: `(bias <= oversold_bias) AND (vol > 0)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("bias-oversold")` is called
- **THEN** it SHALL return a `BIASStrategy` instance

### Requirement: VolumeContractionPullbackStrategy (缩量回调)
The system SHALL provide a `VolumeContractionPullbackStrategy` in the strategy-implementations registry.

Default params: `{"max_vol_ratio": 0.6, "ma_tolerance": 0.02}`

Logic: `(close >= ma20 * (1 - ma_tolerance)) AND (close <= ma20 * (1 + ma_tolerance)) AND (vol_ratio <= max_vol_ratio) AND (ma5 > ma20) AND (vol > 0)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("volume-contraction-pullback")` is called
- **THEN** it SHALL return a `VolumeContractionPullbackStrategy` instance

### Requirement: VolumePriceDivergenceStrategy (量价背离)
The system SHALL provide a `VolumePriceDivergenceStrategy` in the strategy-implementations registry.

Default params: `{"lookback": 20}`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("volume-price-divergence")` is called
- **THEN** it SHALL return a `VolumePriceDivergenceStrategy` instance

### Requirement: OBVBreakthroughStrategy (OBV能量潮突破)
The system SHALL provide an `OBVBreakthroughStrategy` in the strategy-implementations registry.

Default params: `{"lookback": 20}`

Logic: `(obv > obv_max_lookback) AND (close > prev_close) AND (vol > 0)`

#### Scenario: Strategy registered
- **WHEN** `StrategyFactory.get_strategy("obv-breakthrough")` is called
- **THEN** it SHALL return an `OBVBreakthroughStrategy` instance

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
