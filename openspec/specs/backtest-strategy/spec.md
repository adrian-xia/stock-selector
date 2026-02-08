## ADDED Requirements

### Requirement: AStockStrategy base class
The system SHALL provide an `AStockStrategy` class extending `bt.Strategy` that serves as the base class for all A-stock backtest strategies.

`AStockStrategy` SHALL:
- Accept `strategy_name` and `strategy_params` as Backtrader params
- Maintain a `PriceLimitChecker` instance
- Record daily portfolio value in `equity_curve` list during `next()`
- Check price limits before placing any order
- Log trades via `notify_trade()`

#### Scenario: Equity curve recorded daily
- **WHEN** `next()` is called on each bar
- **THEN** the strategy SHALL append `{"date": current_date, "value": broker.getvalue()}` to the equity curve list

#### Scenario: Price limit check before buy
- **WHEN** the strategy attempts to buy a stock that is at limit-up (涨停)
- **THEN** the order SHALL NOT be placed and a log message SHALL be recorded

#### Scenario: Price limit check before sell
- **WHEN** the strategy attempts to sell a stock that is at limit-down (跌停)
- **THEN** the order SHALL NOT be placed and a log message SHALL be recorded

### Requirement: SignalStrategy for generic backtesting
The system SHALL provide a `SignalStrategy` extending `AStockStrategy` that implements a generic buy/sell logic.

Params:
- `hold_days: int` (default 5) — number of days to hold after buying
- `stop_loss_pct: float` (default 0.05) — stop loss percentage (5%)

Buy logic: On each bar, if not in position and `vol > 0` (not suspended), place a buy order.
Sell logic: Sell if held for `hold_days` bars OR if unrealized loss exceeds `stop_loss_pct`.

#### Scenario: Buy on first available bar
- **WHEN** the strategy starts and the stock is tradeable (vol > 0, not at limit-up)
- **THEN** it SHALL place a buy order

#### Scenario: Sell after hold period
- **WHEN** a position has been held for `hold_days` bars
- **THEN** it SHALL place a sell order (if not at limit-down)

#### Scenario: Stop loss triggered
- **WHEN** unrealized loss exceeds `stop_loss_pct`
- **THEN** it SHALL place a sell order immediately (if not at limit-down)

### Requirement: PriceLimitChecker
The system SHALL provide a `PriceLimitChecker` class that determines whether a stock is at price limit.

Price limit rules by board:
- Main board (codes starting with 60xxxx, 00xxxx): ±10%
- ChiNext/STAR (codes starting with 30xxxx, 68xxxx): ±20%
- ST stocks (name contains "ST"): ±5%

Limit-up formula: `close >= round(pre_close * (1 + limit_pct), 2) - 0.01`
Limit-down formula: `close <= round(pre_close * (1 - limit_pct), 2) + 0.01`

#### Scenario: Main board limit-up detected
- **WHEN** a main board stock has `pre_close=10.00` and `close=11.00`
- **THEN** `is_limit_up()` SHALL return `True`

#### Scenario: ChiNext limit-up detected
- **WHEN** a ChiNext stock (300xxx) has `pre_close=10.00` and `close=12.00`
- **THEN** `is_limit_up()` SHALL return `True`

#### Scenario: Not at limit
- **WHEN** a stock has `pre_close=10.00` and `close=10.50`
- **THEN** both `is_limit_up()` and `is_limit_down()` SHALL return `False`

#### Scenario: ST stock limit
- **WHEN** an ST stock has `pre_close=10.00` and `close=10.50`
- **THEN** `is_limit_up()` SHALL return `True` (5% limit)

### Requirement: ChinaStockCommission
The system SHALL provide a `ChinaStockCommission` class extending `bt.CommInfoBase` that models A-stock trading costs.

Fee structure:
- Commission: 0.025% (万2.5) on both buy and sell, minimum 5 CNY per trade
- Stamp duty: 0.1% (千1) on sell only
- Transfer fee: ignored

#### Scenario: Buy commission calculated
- **WHEN** buying 1000 shares at 10.00 CNY (total 10,000 CNY)
- **THEN** commission SHALL be max(10000 * 0.00025, 5) = 5.00 CNY

#### Scenario: Sell commission with stamp duty
- **WHEN** selling 1000 shares at 10.00 CNY (total 10,000 CNY)
- **THEN** total cost SHALL be max(10000 * 0.00025, 5) + 10000 * 0.001 = 5.00 + 10.00 = 15.00 CNY

### Requirement: Position sizing for equal weight
The system SHALL calculate position size using equal weight allocation.

Formula: `shares = floor(available_cash / n_stocks / price / 100) * 100`

Shares SHALL be rounded down to the nearest 100 (A-stock lot size).

#### Scenario: Equal weight sizing
- **WHEN** total cash is 1,000,000 CNY, 5 stocks, current price is 25.00 CNY
- **THEN** position size SHALL be `floor(200000 / 25 / 100) * 100 = 8000` shares
