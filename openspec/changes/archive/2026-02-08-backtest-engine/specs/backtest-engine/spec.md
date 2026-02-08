## ADDED Requirements

### Requirement: BacktestEngine execution entry point
The system SHALL provide a `BacktestEngine` class that configures and runs Backtrader Cerebro for backtesting.

`BacktestEngine.run()` SHALL accept:
- `task_id: int` — the backtest task ID from database
- `stock_codes: list[str]` — stock codes to backtest
- `strategy_name: str` — the strategy identifier
- `strategy_params: dict` — strategy parameters
- `start_date: date` — backtest start date
- `end_date: date` — backtest end date
- `initial_capital: float` — starting capital (default 1,000,000)

The method SHALL be synchronous (Backtrader is a sync framework).

#### Scenario: Single stock backtest
- **WHEN** `BacktestEngine.run()` is called with one stock code and a date range
- **THEN** it SHALL configure Cerebro, load data, execute the strategy, and return a result dict containing performance metrics, trades, and equity curve

#### Scenario: Multi-stock backtest
- **WHEN** `BacktestEngine.run()` is called with multiple stock codes
- **THEN** it SHALL add one DataFeed per stock, allocate capital equally, and execute the strategy across all stocks

### Requirement: Cerebro configuration for A-stock market
The `BacktestEngine` SHALL configure Cerebro with A-stock specific settings:
- Initial cash from `initial_capital` parameter
- `ChinaStockCommission` as the commission model
- Slippage of 0.1% (`broker.set_slippage_perc(0.001)`)
- `cheat_on_open=False` to prevent lookahead bias
- `runonce=False` for step-by-step execution

#### Scenario: Anti-lookahead configuration
- **WHEN** Cerebro is configured
- **THEN** `cheat_on_open` SHALL be `False` to ensure orders placed on bar N are executed at bar N+1 open price

### Requirement: Analyzers configuration
The `BacktestEngine` SHALL add the following Backtrader Analyzers to Cerebro:
- `bt.analyzers.SharpeRatio` (timeframe=Days, annualize=True)
- `bt.analyzers.DrawDown`
- `bt.analyzers.TradeAnalyzer`
- `bt.analyzers.Returns`

#### Scenario: Analyzers available after run
- **WHEN** a backtest completes
- **THEN** the strategy instance SHALL have analyzers accessible via `strat.analyzers.sharpe`, `strat.analyzers.drawdown`, `strat.analyzers.trades`, `strat.analyzers.returns`

### Requirement: PandasDataPlus custom DataFeed
The system SHALL provide a `PandasDataPlus` class extending `bt.feeds.PandasData` with additional lines:
- `turnover_rate`
- `adj_factor`

#### Scenario: DataFeed loads from DataFrame
- **WHEN** a pandas DataFrame with columns `open, high, low, close, vol, turnover_rate, adj_factor` is provided
- **THEN** `PandasDataPlus` SHALL map these columns correctly to Backtrader lines

### Requirement: Data loading with forward adjustment
The system SHALL provide a `load_stock_data()` async function that queries `stock_daily` and applies dynamic forward adjustment (前复权).

Forward adjustment formula: `price_adj = price_raw * (adj_factor / latest_adj_factor)`

The function SHALL:
- Query `stock_daily` for the given stock code and date range
- Apply forward adjustment to open, high, low, close prices
- Retain rows where `vol = 0` (suspended days) without removing them
- Return a pandas DataFrame sorted by trade_date ascending

#### Scenario: Forward adjustment applied correctly
- **WHEN** stock data is loaded for a stock that had a 10-for-1 split
- **THEN** historical prices SHALL be adjusted so the price series is continuous

#### Scenario: Suspended days retained
- **WHEN** stock data contains days with `vol = 0`
- **THEN** those rows SHALL remain in the DataFrame (Backtrader needs them to know trading is not possible)

### Requirement: Async wrapper for API integration
The system SHALL provide an `async run_backtest()` function that wraps the synchronous `BacktestEngine.run()` using `asyncio.get_event_loop().run_in_executor()`.

#### Scenario: Non-blocking execution in async context
- **WHEN** `run_backtest()` is called from a FastAPI async endpoint
- **THEN** it SHALL execute the backtest in a thread pool without blocking the event loop
