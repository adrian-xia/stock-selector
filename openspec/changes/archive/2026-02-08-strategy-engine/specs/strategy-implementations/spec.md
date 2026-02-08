## ADDED Requirements

### Requirement: MACrossStrategy (均线金叉)
The system SHALL provide a `MACrossStrategy` that detects short-term MA crossing above long-term MA with volume confirmation.

Default params: `{"fast": 5, "slow": 10, "vol_ratio": 1.5}`

Logic: `(prev_ma_fast <= prev_ma_slow) AND (ma_fast > ma_slow) AND (vol > vol_ma5 * vol_ratio) AND (vol > 0)`

The strategy SHALL use `ma{fast}`, `ma{slow}`, `vol_ma5` columns from the input DataFrame. Previous-day values SHALL be derived by joining with the prior trading day's data or by using pre-computed `_prev` columns if available.

#### Scenario: Golden cross detected
- **WHEN** yesterday MA5 <= MA10 and today MA5 > MA10 and today vol > vol_ma5 * 1.5
- **THEN** the strategy SHALL return `True` for that stock

#### Scenario: No cross
- **WHEN** MA5 has been above MA10 for multiple days (no crossover)
- **THEN** the strategy SHALL return `False`

### Requirement: MACDGoldenStrategy (MACD金叉)
The system SHALL provide a `MACDGoldenStrategy` that detects DIF crossing above DEA.

Default params: `{}`

Logic: `(prev_dif <= prev_dea) AND (macd_dif > macd_dea) AND (vol > 0)`

#### Scenario: MACD golden cross
- **WHEN** yesterday DIF <= DEA and today DIF > DEA
- **THEN** the strategy SHALL return `True`

### Requirement: RSIOversoldStrategy (RSI超卖反弹)
The system SHALL provide a `RSIOversoldStrategy` that detects RSI bouncing from oversold territory.

Default params: `{"period": 6, "oversold": 20, "bounce": 30}`

Logic: `(rsi{period} > bounce) AND (prev_rsi{period} <= oversold)`

#### Scenario: RSI bounce from oversold
- **WHEN** yesterday RSI6 was 18 (below 20) and today RSI6 is 32 (above 30)
- **THEN** the strategy SHALL return `True`

### Requirement: KDJGoldenStrategy (KDJ金叉)
The system SHALL provide a `KDJGoldenStrategy` that detects K crossing above D in oversold territory.

Default params: `{"oversold_j": 20}`

Logic: `(prev_kdj_k <= prev_kdj_d) AND (kdj_k > kdj_d) AND (kdj_j < oversold_j)`

#### Scenario: KDJ golden cross in oversold zone
- **WHEN** yesterday K <= D and today K > D and J < 20
- **THEN** the strategy SHALL return `True`

### Requirement: BollBreakthroughStrategy (布林带突破)
The system SHALL provide a `BollBreakthroughStrategy` that detects price bouncing from below the lower Bollinger Band.

Default params: `{}`

Logic: `(prev_close <= prev_boll_lower) AND (close > boll_lower) AND (vol > 0)`

#### Scenario: Price bounces from lower band
- **WHEN** yesterday close was at or below lower band and today close is above lower band
- **THEN** the strategy SHALL return `True`

### Requirement: VolumeBreakoutStrategy (放量突破)
The system SHALL provide a `VolumeBreakoutStrategy` that detects price breaking 20-day high with heavy volume.

Default params: `{"high_period": 20, "min_vol_ratio": 2.0}`

Logic: `(close >= max_high_20) AND (vol_ratio >= min_vol_ratio) AND (vol > 0)`

The `max_high_20` SHALL be the highest `high` price over the past 20 trading days (excluding today).

#### Scenario: Volume breakout detected
- **WHEN** today's close >= 20-day high and vol_ratio >= 2.0
- **THEN** the strategy SHALL return `True`

### Requirement: MALongArrangeStrategy (均线多头排列)
The system SHALL provide a `MALongArrangeStrategy` that detects bullish MA alignment.

Default params: `{}`

Logic: `(ma5 > ma10) AND (ma10 > ma20) AND (ma20 > ma60) AND (vol > 0)`

#### Scenario: Bullish MA alignment
- **WHEN** MA5 > MA10 > MA20 > MA60 and stock is trading
- **THEN** the strategy SHALL return `True`

#### Scenario: Partial alignment
- **WHEN** MA5 > MA10 > MA20 but MA20 < MA60
- **THEN** the strategy SHALL return `False`

### Requirement: MACDDivergenceStrategy (MACD底背离)
The system SHALL provide a `MACDDivergenceStrategy` that detects bullish divergence between price and MACD.

Default params: `{"lookback": 20}`

Logic: Over the past `lookback` days, if the current close is lower than a previous local minimum close, but the current MACD DIF is higher than the DIF at that previous minimum, a bullish divergence is detected.

#### Scenario: Bullish divergence detected
- **WHEN** price makes a new low but MACD DIF does not make a new low over the lookback period
- **THEN** the strategy SHALL return `True`

### Requirement: LowPEHighROEStrategy (低估值高成长)
The system SHALL provide a `LowPEHighROEStrategy` that filters by PE and ROE thresholds.

Default params: `{"pe_max": 30, "roe_min": 15, "profit_growth_min": 20}`

Logic: `(pe_ttm > 0) AND (pe_ttm < pe_max) AND (roe >= roe_min) AND (profit_yoy >= profit_growth_min)`

#### Scenario: Stock meets value criteria
- **WHEN** PE_TTM = 15, ROE = 20%, profit_yoy = 25%
- **THEN** the strategy SHALL return `True`

#### Scenario: Negative PE excluded
- **WHEN** PE_TTM = -5 (loss-making company)
- **THEN** the strategy SHALL return `False`

### Requirement: HighDividendStrategy (高股息)
The system SHALL provide a `HighDividendStrategy` that filters by dividend yield and PE.

Default params: `{"min_dividend_yield": 3.0, "pe_max": 20}`

This strategy requires a `dividend_yield` column. If the column is not present or is NaN, the strategy SHALL return `False`.

#### Scenario: High dividend stock
- **WHEN** dividend_yield = 4.5% and PE = 12
- **THEN** the strategy SHALL return `True`

### Requirement: GrowthStockStrategy (成长股)
The system SHALL provide a `GrowthStockStrategy` that filters by revenue and profit growth.

Default params: `{"revenue_growth_min": 20, "profit_growth_min": 20}`

Logic: `(revenue_yoy >= revenue_growth_min) AND (profit_yoy >= profit_growth_min)`

#### Scenario: High growth stock
- **WHEN** revenue_yoy = 30% and profit_yoy = 25%
- **THEN** the strategy SHALL return `True`

### Requirement: FinancialSafetyStrategy (财务安全)
The system SHALL provide a `FinancialSafetyStrategy` that filters by debt and liquidity ratios.

Default params: `{"debt_ratio_max": 60, "current_ratio_min": 1.5}`

Logic: `(debt_ratio < debt_ratio_max) AND (current_ratio >= current_ratio_min)`

#### Scenario: Financially safe stock
- **WHEN** debt_ratio = 45% and current_ratio = 2.0
- **THEN** the strategy SHALL return `True`

#### Scenario: High debt stock excluded
- **WHEN** debt_ratio = 75%
- **THEN** the strategy SHALL return `False`
