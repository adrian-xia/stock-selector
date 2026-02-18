## ADDED Requirements

### Requirement: CCIOverboughtOversoldStrategy (CCI超买超卖)
The system SHALL provide a `CCIOverboughtOversoldStrategy` that detects CCI bouncing from oversold territory.

Default params: `{"oversold": -100, "bounce": -80}`

Logic: `(prev_cci <= oversold) AND (cci > bounce) AND (vol > 0)`

#### Scenario: CCI bounce from oversold
- **WHEN** yesterday CCI <= -100 and today CCI > -80
- **THEN** the strategy SHALL return `True`

#### Scenario: CCI still in oversold zone
- **WHEN** yesterday CCI = -120 and today CCI = -110 (still below bounce threshold)
- **THEN** the strategy SHALL return `False`

#### Scenario: Missing CCI data
- **WHEN** cci is NaN
- **THEN** the strategy SHALL return `False`

### Requirement: WilliamsRStrategy (Williams %R 超卖反弹)
The system SHALL provide a `WilliamsRStrategy` that detects Williams %R bouncing from oversold territory.

Default params: `{"oversold": -80, "bounce": -50}`

Logic: `(prev_wr <= oversold) AND (wr > bounce) AND (vol > 0)`

Williams %R range is [-100, 0]. Values below -80 indicate oversold.

#### Scenario: WR bounce from oversold
- **WHEN** yesterday WR <= -80 and today WR > -50
- **THEN** the strategy SHALL return `True`

#### Scenario: WR still oversold
- **WHEN** yesterday WR = -90 and today WR = -85 (above oversold but below bounce)
- **THEN** the strategy SHALL return `False`

#### Scenario: Missing WR data
- **WHEN** wr is NaN
- **THEN** the strategy SHALL return `False`

### Requirement: BIASStrategy (BIAS乖离率)
The system SHALL provide a `BIASStrategy` that detects price deviation from MA20 reaching oversold levels and reverting.

Default params: `{"oversold_bias": -6.0}`

Logic: `(bias <= oversold_bias) AND (vol > 0)`

BIAS = (close - MA20) / MA20 * 100. Negative BIAS indicates price below MA20. When BIAS reaches extreme negative values, a mean-reversion bounce is expected.

#### Scenario: BIAS oversold signal
- **WHEN** BIAS = -7.5 (below -6.0 threshold) and vol > 0
- **THEN** the strategy SHALL return `True`

#### Scenario: BIAS not extreme enough
- **WHEN** BIAS = -3.0 (above -6.0 threshold)
- **THEN** the strategy SHALL return `False`

#### Scenario: Missing BIAS data
- **WHEN** bias is NaN
- **THEN** the strategy SHALL return `False`
