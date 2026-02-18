## ADDED Requirements

### Requirement: Williams %R indicator calculation
The system SHALL compute Williams %R with period 14 using the formula:

`WR = (highest_high_14 - close) / (highest_high_14 - lowest_low_14) * -100`

When `highest_high_14 == lowest_low_14`, WR SHALL be set to -50 (midpoint).

The result SHALL be stored in the `wr` column of `technical_daily` with Numeric(10,4) precision.

#### Scenario: Normal WR calculation
- **WHEN** 14-day highest high = 15.0, lowest low = 10.0, close = 11.0
- **THEN** WR = (15.0 - 11.0) / (15.0 - 10.0) * -100 = -80.0

#### Scenario: Flat price (no range)
- **WHEN** highest_high_14 == lowest_low_14
- **THEN** WR SHALL be -50.0

### Requirement: CCI indicator calculation
The system SHALL compute CCI with period 14 using the formula:

`TP = (high + low + close) / 3`
`CCI = (TP - SMA(TP, 14)) / (0.015 * MAD(TP, 14))`

Where MAD is the Mean Absolute Deviation of TP over 14 periods.

When MAD == 0, CCI SHALL be set to 0.

The result SHALL be stored in the `cci` column of `technical_daily` with Numeric(10,4) precision.

#### Scenario: Normal CCI calculation
- **WHEN** TP deviates significantly above its 14-day SMA
- **THEN** CCI SHALL be a large positive number (e.g., > 100)

#### Scenario: Zero MAD
- **WHEN** all 14 TP values are identical (MAD = 0)
- **THEN** CCI SHALL be 0

### Requirement: BIAS indicator calculation
The system SHALL compute BIAS based on MA20 using the formula:

`BIAS = (close - MA20) / MA20 * 100`

When MA20 is NaN or 0, BIAS SHALL be NaN.

The result SHALL be stored in the `bias` column of `technical_daily` with Numeric(10,4) precision.

#### Scenario: Price above MA20
- **WHEN** close = 11.0 and MA20 = 10.0
- **THEN** BIAS = (11.0 - 10.0) / 10.0 * 100 = 10.0

#### Scenario: Price below MA20
- **WHEN** close = 9.0 and MA20 = 10.0
- **THEN** BIAS = (9.0 - 10.0) / 10.0 * 100 = -10.0

#### Scenario: MA20 not available
- **WHEN** MA20 is NaN (insufficient data)
- **THEN** BIAS SHALL be NaN

### Requirement: OBV indicator calculation
The system SHALL compute OBV (On-Balance Volume) using the formula:

`OBV(t) = OBV(t-1) + sign(close(t) - close(t-1)) * vol(t)`

Where sign returns +1 if positive, -1 if negative, 0 if unchanged. OBV(0) = 0.

The result SHALL be stored in the `obv` column of `technical_daily` with Numeric(20,2) precision.

#### Scenario: Price increase
- **WHEN** close increases from 10.0 to 11.0 with vol = 1000
- **THEN** OBV increases by 1000

#### Scenario: Price decrease
- **WHEN** close decreases from 11.0 to 10.0 with vol = 800
- **THEN** OBV decreases by 800

#### Scenario: Price unchanged
- **WHEN** close is unchanged with vol = 500
- **THEN** OBV remains unchanged (vol contribution = 0)

### Requirement: Donchian channel indicator calculation
The system SHALL compute Donchian channel upper and lower bands with period 20:

`donchian_upper = max(high) over past 20 trading days (excluding today)`
`donchian_lower = min(low) over past 20 trading days (excluding today)`

The results SHALL be stored in `donchian_upper` (Numeric(10,2)) and `donchian_lower` (Numeric(10,2)) columns of `technical_daily`.

#### Scenario: Normal Donchian calculation
- **WHEN** past 20 days highest high = 15.0 and lowest low = 10.0
- **THEN** donchian_upper = 15.0 and donchian_lower = 10.0

#### Scenario: Insufficient data
- **WHEN** fewer than 20 trading days of history
- **THEN** donchian_upper and donchian_lower SHALL be NaN
