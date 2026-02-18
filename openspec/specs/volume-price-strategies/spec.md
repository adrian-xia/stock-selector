## ADDED Requirements

### Requirement: VolumeContractionPullbackStrategy (缩量回调)
The system SHALL provide a `VolumeContractionPullbackStrategy` that detects low-volume pullbacks to MA20 support in an uptrend.

Default params: `{"max_vol_ratio": 0.6, "ma_tolerance": 0.02}`

Logic: `(close >= ma20 * (1 - ma_tolerance)) AND (close <= ma20 * (1 + ma_tolerance)) AND (vol_ratio <= max_vol_ratio) AND (ma5 > ma20) AND (vol > 0)`

The strategy identifies stocks in an uptrend (MA5 > MA20) that have pulled back to MA20 support on low volume (vol_ratio <= 0.6), suggesting a potential bounce.

#### Scenario: Volume contraction pullback detected
- **WHEN** MA5 > MA20 and close is within 2% of MA20 and vol_ratio = 0.4
- **THEN** the strategy SHALL return `True`

#### Scenario: High volume pullback (not contraction)
- **WHEN** close is near MA20 but vol_ratio = 1.5
- **THEN** the strategy SHALL return `False`

#### Scenario: Downtrend pullback (not valid)
- **WHEN** MA5 < MA20 (downtrend) even if vol_ratio is low
- **THEN** the strategy SHALL return `False`

#### Scenario: Missing data
- **WHEN** ma20 or vol_ratio is NaN
- **THEN** the strategy SHALL return `False`

### Requirement: VolumePriceDivergenceStrategy (量价背离)
The system SHALL provide a `VolumePriceDivergenceStrategy` that detects bullish divergence between price making new lows and volume declining.

Default params: `{"lookback": 20}`

Logic: Over the past `lookback` days, if the current close is at or near the lowest level but current volume is significantly lower than the volume at the previous price low, a bullish volume-price divergence is detected.

Specifically: `(close <= close_min_lookback * 1.02) AND (vol < vol_at_prev_low * 0.7) AND (vol > 0)`

The strategy SHALL use pre-computed `donchian_lower` (lowest low over lookback period) as a proxy for price low detection, and compare current volume against historical volume levels.

#### Scenario: Bullish volume-price divergence
- **WHEN** price is near 20-day low and current volume is less than 70% of volume at previous low
- **THEN** the strategy SHALL return `True`

#### Scenario: Price at low but volume not declining
- **WHEN** price is near 20-day low but volume is similar or higher than previous
- **THEN** the strategy SHALL return `False`

#### Scenario: Missing data
- **WHEN** required columns contain NaN
- **THEN** the strategy SHALL return `False`

### Requirement: OBVBreakthroughStrategy (OBV能量潮突破)
The system SHALL provide an `OBVBreakthroughStrategy` that detects OBV breaking above its recent high while price confirms.

Default params: `{"lookback": 20}`

Logic: `(obv > obv_max_lookback) AND (close > prev_close) AND (vol > 0)`

Where `obv_max_lookback` is the maximum OBV value over the past `lookback` days (excluding today). The strategy detects accumulation breakouts confirmed by price increase.

#### Scenario: OBV breakthrough detected
- **WHEN** today OBV exceeds 20-day OBV high and close > prev_close
- **THEN** the strategy SHALL return `True`

#### Scenario: OBV high but price declining
- **WHEN** OBV exceeds 20-day high but close < prev_close
- **THEN** the strategy SHALL return `False`

#### Scenario: Missing OBV data
- **WHEN** obv is NaN
- **THEN** the strategy SHALL return `False`
