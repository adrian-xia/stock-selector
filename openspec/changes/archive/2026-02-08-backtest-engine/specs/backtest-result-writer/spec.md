## ADDED Requirements

### Requirement: BacktestResultWriter
The system SHALL provide a `BacktestResultWriter` class that extracts performance metrics from Backtrader Analyzers and persists them to the database.

`BacktestResultWriter.save()` SHALL accept:
- `task_id: int` — the backtest task ID
- `strategy_instance` — the executed Backtrader strategy with analyzers
- `equity_curve: list[dict]` — daily portfolio values

#### Scenario: Save complete results
- **WHEN** `save()` is called after a successful backtest
- **THEN** it SHALL insert one row into `backtest_results` with all performance metrics, trades_json, and equity_curve_json

### Requirement: Performance metrics extraction
The writer SHALL extract the following metrics from Backtrader Analyzers:

From `SharpeRatio`: `sharpe_ratio`
From `DrawDown`: `max_drawdown` (as percentage)
From `Returns`: `total_return`, `annual_return`
From `TradeAnalyzer`: `total_trades`, `win_rate`, `profit_loss_ratio`

Additionally, the writer SHALL calculate:
- `calmar_ratio`: annual_return / max_drawdown (0 if max_drawdown is 0)
- `sortino_ratio`: annual_return / downside_deviation
- `volatility`: annualized standard deviation of daily returns

#### Scenario: Metrics extracted from analyzers
- **WHEN** a backtest completes with SharpeRatio=1.5, MaxDrawdown=15%, TotalReturn=30%
- **THEN** the saved `backtest_results` row SHALL contain `sharpe_ratio=1.5`, `max_drawdown=0.15`, `total_return=0.30`

#### Scenario: No trades executed
- **WHEN** a backtest completes with zero trades (strategy never triggered)
- **THEN** `total_trades` SHALL be 0, `win_rate` SHALL be NULL, and other metrics SHALL reflect the unchanged portfolio

### Requirement: Trades extraction to JSON
The writer SHALL extract trade details from `TradeAnalyzer` and serialize them as a JSON list in `trades_json`.

Each trade entry SHALL contain:
- `stock_code: str`
- `direction: str` ("buy" or "sell")
- `date: str` (ISO format)
- `price: float`
- `size: int`
- `commission: float`
- `pnl: float` (profit/loss, only for closing trades)

#### Scenario: Trades serialized correctly
- **WHEN** a backtest produces 5 buy orders and 5 sell orders
- **THEN** `trades_json` SHALL contain a list of 10 trade entries with correct fields

### Requirement: Equity curve to JSON
The writer SHALL save the equity curve as a JSON list in `equity_curve_json`.

Each entry SHALL contain:
- `date: str` (ISO format)
- `value: float` (portfolio value)

#### Scenario: Daily equity curve saved
- **WHEN** a backtest runs over 250 trading days
- **THEN** `equity_curve_json` SHALL contain 250 entries, one per trading day

### Requirement: Task status update
The writer SHALL update the `backtest_tasks` table status:
- Set `status = 'completed'` on successful save
- Set `status = 'failed'` and `error_message` on failure

#### Scenario: Task marked completed
- **WHEN** results are saved successfully
- **THEN** the corresponding `backtest_tasks` row SHALL have `status = 'completed'`

#### Scenario: Task marked failed
- **WHEN** the backtest raises an exception
- **THEN** the corresponding `backtest_tasks` row SHALL have `status = 'failed'` and `error_message` containing the exception message
