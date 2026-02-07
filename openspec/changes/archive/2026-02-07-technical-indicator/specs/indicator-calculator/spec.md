## ADDED Requirements

### Requirement: compute_single_stock_indicators function
The system SHALL provide a `compute_single_stock_indicators()` function that takes a single stock's daily bar DataFrame and returns a DataFrame with all 23 technical indicator columns computed.

Input DataFrame SHALL contain at minimum: `trade_date`, `open`, `high`, `low`, `close`, `vol` columns sorted by `trade_date` ascending.

Output DataFrame SHALL contain all original columns plus the following indicator columns:
- Moving averages: `ma5`, `ma10`, `ma20`, `ma60`, `ma120`, `ma250`
- MACD: `macd_dif`, `macd_dea`, `macd_hist`
- KDJ: `kdj_k`, `kdj_d`, `kdj_j`
- RSI: `rsi6`, `rsi12`, `rsi24`
- Bollinger Bands: `boll_upper`, `boll_mid`, `boll_lower`
- Volume indicators: `vol_ma5`, `vol_ma10`, `vol_ratio`
- ATR: `atr14`

All calculations SHALL use pandas vectorized operations without external technical analysis libraries.

#### Scenario: Compute indicators for a stock with sufficient history
- **WHEN** `compute_single_stock_indicators(df)` is called with a DataFrame containing 300 days of daily bars
- **THEN** it SHALL return a DataFrame with all 23 indicator columns populated
- **AND** rows where insufficient history exists for a given indicator (e.g., first 249 rows for MA250) SHALL have `NaN` for that indicator

#### Scenario: Compute indicators for a newly listed stock
- **WHEN** `compute_single_stock_indicators(df)` is called with a DataFrame containing only 30 days of data
- **THEN** indicators requiring more history (MA60, MA120, MA250) SHALL be `NaN`
- **AND** indicators with sufficient data (MA5, MA10, MA20, RSI6, KDJ) SHALL be computed normally

#### Scenario: Empty DataFrame input
- **WHEN** `compute_single_stock_indicators(df)` is called with an empty DataFrame
- **THEN** it SHALL return an empty DataFrame with the correct column schema

### Requirement: MA (Simple Moving Average) calculation
The system SHALL compute simple moving averages using the formula: `MA(N) = sum(close[-N:]) / N`.

Supported periods: 5, 10, 20, 60, 120, 250.

#### Scenario: MA5 calculation
- **WHEN** the last 5 closing prices are [10.0, 10.5, 11.0, 10.8, 11.2]
- **THEN** MA5 SHALL equal 10.70

#### Scenario: Insufficient data for MA250
- **WHEN** a stock has only 100 days of history
- **THEN** MA250 SHALL be `NaN` for all rows
- **AND** MA60 SHALL be `NaN` for the first 59 rows and computed from row 60 onward

### Requirement: MACD calculation
The system SHALL compute MACD using standard parameters (12, 26, 9):
- `macd_dif` = EMA(close, 12) - EMA(close, 26)
- `macd_dea` = EMA(macd_dif, 9)
- `macd_hist` = 2 * (macd_dif - macd_dea)

EMA SHALL use the standard exponential moving average formula: `EMA(t) = close(t) * α + EMA(t-1) * (1 - α)` where `α = 2 / (N + 1)`.

#### Scenario: MACD calculation with sufficient data
- **WHEN** a stock has 60 days of closing prices
- **THEN** `macd_dif`, `macd_dea`, `macd_hist` SHALL all be computed
- **AND** the first 25 rows of `macd_dif` SHALL be `NaN` (insufficient for EMA26)

### Requirement: KDJ calculation
The system SHALL compute KDJ using standard parameters (9, 3, 3):
1. RSV = (close - lowest_low(9)) / (highest_high(9) - lowest_low(9)) * 100
2. K = EMA(RSV, 3) with initial K = 50
3. D = EMA(K, 3) with initial D = 50
4. J = 3 * K - 2 * D

When `highest_high(9) == lowest_low(9)`, RSV SHALL be set to 50.

#### Scenario: KDJ calculation
- **WHEN** a stock has 20 days of OHLC data
- **THEN** `kdj_k`, `kdj_d`, `kdj_j` SHALL be computed from row 9 onward
- **AND** K and D values SHALL be initialized to 50

#### Scenario: KDJ with flat price (no range)
- **WHEN** the highest high and lowest low in the 9-day window are equal
- **THEN** RSV SHALL be 50 (not division by zero)

### Requirement: RSI calculation
The system SHALL compute RSI using the formula:
1. Calculate price changes: `delta = close - close.shift(1)`
2. Separate gains and losses: `gain = max(delta, 0)`, `loss = abs(min(delta, 0))`
3. Average gain/loss using EMA (Wilder's smoothing): `avg_gain = EMA(gain, N)`, `avg_loss = EMA(loss, N)`
4. RS = avg_gain / avg_loss
5. RSI = 100 - 100 / (1 + RS)

Supported periods: 6, 12, 24.

When `avg_loss == 0`, RSI SHALL be 100. When `avg_gain == 0`, RSI SHALL be 0.

#### Scenario: RSI6 calculation
- **WHEN** a stock has 30 days of closing prices
- **THEN** `rsi6` SHALL be computed from row 7 onward
- **AND** RSI values SHALL be in the range [0, 100]

#### Scenario: RSI with all gains (no losses)
- **WHEN** closing prices are monotonically increasing over the RSI period
- **THEN** RSI SHALL be 100

### Requirement: Bollinger Bands calculation
The system SHALL compute Bollinger Bands using parameters (20, 2):
- `boll_mid` = MA(close, 20)
- `boll_upper` = boll_mid + 2 * STD(close, 20)
- `boll_lower` = boll_mid - 2 * STD(close, 20)

STD SHALL use population standard deviation (`ddof=0`).

#### Scenario: Bollinger Bands calculation
- **WHEN** a stock has 30 days of closing prices
- **THEN** `boll_upper`, `boll_mid`, `boll_lower` SHALL be computed from row 20 onward
- **AND** `boll_upper > boll_mid > boll_lower` SHALL always hold

### Requirement: Volume indicators calculation
The system SHALL compute:
- `vol_ma5` = MA(vol, 5)
- `vol_ma10` = MA(vol, 10)
- `vol_ratio` = vol / vol_ma5 (当日成交量与5日均量的比值)

When `vol_ma5 == 0`, `vol_ratio` SHALL be `NaN`.

#### Scenario: Volume ratio calculation
- **WHEN** today's volume is 1500 and the 5-day average volume is 1000
- **THEN** `vol_ratio` SHALL be 1.5

#### Scenario: Volume ratio with zero average
- **WHEN** the 5-day average volume is 0 (e.g., stock was suspended)
- **THEN** `vol_ratio` SHALL be `NaN`

### Requirement: ATR14 calculation
The system SHALL compute ATR (Average True Range) with period 14:
1. True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
2. ATR14 = EMA(True Range, 14)

#### Scenario: ATR14 calculation
- **WHEN** a stock has 20 days of OHLC data
- **THEN** `atr14` SHALL be computed from row 15 onward
- **AND** ATR14 SHALL always be >= 0

### Requirement: compute_all_stocks full market batch computation
The system SHALL provide a `compute_all_stocks()` async function that:
1. Queries all listed stocks from the `stocks` table
2. For each stock, loads up to 300 days of daily bar history from `stock_daily`
3. Computes all technical indicators using `compute_single_stock_indicators()`
4. Writes results to `technical_daily` using UPSERT (INSERT ... ON CONFLICT DO UPDATE)
5. Commits in batches (every 100 stocks) to avoid long transactions
6. Returns a summary dict with counts

#### Scenario: Full market computation
- **WHEN** `compute_all_stocks(session_factory)` is called
- **THEN** it SHALL compute indicators for all listed stocks
- **AND** write results to `technical_daily`
- **AND** return `{"total": N, "success": M, "failed": F, "elapsed_seconds": T}`

#### Scenario: Stock with no daily data
- **WHEN** a stock exists in `stocks` but has no records in `stock_daily`
- **THEN** it SHALL be skipped and counted in the summary
- **AND** no error SHALL be raised

### Requirement: compute_incremental daily incremental computation
The system SHALL provide a `compute_incremental()` async function that:
1. Determines the latest trading day from `stock_daily`
2. For each stock that has data on that trading day, loads 300 days of history
3. Computes indicators and UPSERT only the latest trading day's row into `technical_daily`
4. Returns a summary dict

#### Scenario: Incremental computation for latest trading day
- **WHEN** `compute_incremental(session_factory)` is called after daily data sync
- **THEN** it SHALL compute indicators only for the most recent trading day
- **AND** UPSERT results into `technical_daily`
- **AND** return `{"trade_date": "2026-02-07", "total": N, "success": M, "failed": F}`

#### Scenario: Incremental computation with specific date
- **WHEN** `compute_incremental(session_factory, target_date=date(2026, 2, 6))` is called
- **THEN** it SHALL compute indicators for the specified date instead of the latest
