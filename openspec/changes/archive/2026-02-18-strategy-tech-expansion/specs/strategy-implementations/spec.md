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
