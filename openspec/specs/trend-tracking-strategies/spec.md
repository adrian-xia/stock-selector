## ADDED Requirements

### Requirement: DonchianBreakoutStrategy (唐奇安通道突破)
The system SHALL provide a `DonchianBreakoutStrategy` that detects price breaking above the 20-day Donchian channel upper band.

Default params: `{"period": 20}`

Logic: `(prev_close <= prev_donchian_upper) AND (close > donchian_upper) AND (vol > 0)`

The strategy SHALL use pre-computed `donchian_upper` column from `technical_daily`. The Donchian upper band is the highest high over the past N trading days (excluding today).

#### Scenario: Donchian breakout detected
- **WHEN** yesterday close <= donchian_upper and today close > donchian_upper and vol > 0
- **THEN** the strategy SHALL return `True` for that stock

#### Scenario: Price already above channel
- **WHEN** yesterday close was already above donchian_upper (no breakout crossover)
- **THEN** the strategy SHALL return `False`

#### Scenario: Missing donchian_upper data
- **WHEN** donchian_upper is NaN for a stock
- **THEN** the strategy SHALL return `False`

### Requirement: ATRBreakoutStrategy (ATR波动率突破)
The system SHALL provide an `ATRBreakoutStrategy` that detects price breaking above MA20 + ATR14 multiplier.

Default params: `{"atr_multiplier": 1.5}`

Logic: `(close > ma20 + atr14 * atr_multiplier) AND (prev_close <= prev_ma20 + prev_atr14 * atr_multiplier) AND (vol > 0)`

The strategy SHALL use `close`, `ma20`, `atr14` columns and their `_prev` counterparts.

#### Scenario: ATR breakout detected
- **WHEN** today close > MA20 + 1.5 * ATR14 and yesterday close <= MA20_prev + 1.5 * ATR14_prev
- **THEN** the strategy SHALL return `True`

#### Scenario: Already above ATR band
- **WHEN** price has been above MA20 + 1.5 * ATR14 for multiple days
- **THEN** the strategy SHALL return `False`

#### Scenario: Missing ATR data
- **WHEN** atr14 or ma20 is NaN
- **THEN** the strategy SHALL return `False`
