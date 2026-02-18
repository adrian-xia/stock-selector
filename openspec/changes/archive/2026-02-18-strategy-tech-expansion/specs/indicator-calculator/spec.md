## MODIFIED Requirements

### Requirement: indicator_calculator computes extended indicators
The `compute_indicators_generic` function SHALL compute 29 technical indicators (existing 23 + 6 new):

New indicators:
- `wr`: Williams %R (period 14)
- `cci`: CCI (period 14)
- `bias`: BIAS based on MA20
- `obv`: On-Balance Volume (cumulative)
- `donchian_upper`: Donchian channel upper band (period 20)
- `donchian_lower`: Donchian channel lower band (period 20)

The `INDICATOR_COLUMNS` list SHALL include all 29 indicator column names.

#### Scenario: All 29 indicators computed
- **WHEN** `compute_indicators_generic(df)` is called with valid OHLCV data
- **THEN** the result DataFrame SHALL contain 29 indicator columns including wr, cci, bias, obv, donchian_upper, donchian_lower

#### Scenario: Empty DataFrame
- **WHEN** `compute_indicators_generic(df)` is called with an empty DataFrame
- **THEN** the result SHALL contain all 29 indicator columns with float64 dtype
