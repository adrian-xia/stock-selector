## ADDED Requirements

### Requirement: POST /api/v1/backtest/run endpoint
The system SHALL provide a `POST /api/v1/backtest/run` endpoint that accepts a backtest request and returns results synchronously.

Request body:
```json
{
  "strategy_name": "ma-cross",
  "strategy_params": {"fast": 5, "slow": 10},
  "stock_codes": ["600519.SH", "000858.SZ"],
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "initial_capital": 1000000
}
```

- `strategy_name`: strategy identifier (required)
- `strategy_params`: parameter overrides (optional, default `{}`)
- `stock_codes`: list of stock codes to backtest (required, at least one)
- `start_date`: backtest start date in ISO format (required)
- `end_date`: backtest end date in ISO format (required)
- `initial_capital`: starting capital in CNY (optional, default 1,000,000)

Response body:
```json
{
  "task_id": 42,
  "status": "completed",
  "result": {
    "total_return": 0.2534,
    "annual_return": 0.1245,
    "max_drawdown": 0.0823,
    "sharpe_ratio": 1.52,
    "win_rate": 0.65,
    "profit_loss_ratio": 2.1,
    "total_trades": 12,
    "calmar_ratio": 1.51,
    "volatility": 0.18,
    "elapsed_ms": 3200
  }
}
```

#### Scenario: Successful backtest execution
- **WHEN** `POST /api/v1/backtest/run` is called with valid parameters
- **THEN** it SHALL return HTTP 200 with task_id, status "completed", and result metrics

#### Scenario: Invalid strategy name
- **WHEN** `POST /api/v1/backtest/run` is called with an unknown strategy_name
- **THEN** it SHALL return HTTP 400 with an error message listing available strategies

#### Scenario: Empty stock codes
- **WHEN** `POST /api/v1/backtest/run` is called with `stock_codes: []`
- **THEN** it SHALL return HTTP 422 validation error

#### Scenario: Invalid date range
- **WHEN** `start_date` is after `end_date`
- **THEN** it SHALL return HTTP 400 with an error message

#### Scenario: Backtest execution failure
- **WHEN** the backtest engine raises an exception (e.g., no data for the stock)
- **THEN** it SHALL return HTTP 200 with status "failed" and an error_message field

### Requirement: GET /api/v1/backtest/result/{task_id} endpoint
The system SHALL provide a `GET /api/v1/backtest/result/{task_id}` endpoint that returns the full backtest result including trades and equity curve.

Response body:
```json
{
  "task_id": 42,
  "status": "completed",
  "strategy_name": "ma-cross",
  "stock_codes": ["600519.SH"],
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "result": {
    "total_return": 0.2534,
    "annual_return": 0.1245,
    "max_drawdown": 0.0823,
    "sharpe_ratio": 1.52,
    "win_rate": 0.65,
    "total_trades": 12
  },
  "trades": [...],
  "equity_curve": [...]
}
```

#### Scenario: Get completed result
- **WHEN** `GET /api/v1/backtest/result/42` is called for a completed task
- **THEN** it SHALL return HTTP 200 with full result including trades and equity_curve

#### Scenario: Get pending result
- **WHEN** `GET /api/v1/backtest/result/42` is called for a task still running
- **THEN** it SHALL return HTTP 200 with `status: "running"` and null result

#### Scenario: Task not found
- **WHEN** `GET /api/v1/backtest/result/999` is called for a non-existent task
- **THEN** it SHALL return HTTP 404

### Requirement: Backtest task lifecycle
The API SHALL manage backtest task status in the `backtest_tasks` table:
- Create task with `status = 'pending'` before execution
- Update to `status = 'running'` when execution starts
- Update to `status = 'completed'` on success
- Update to `status = 'failed'` with `error_message` on failure

#### Scenario: Task status transitions
- **WHEN** a backtest is submitted and completes successfully
- **THEN** the task status SHALL transition: pending → running → completed

#### Scenario: Task failure recorded
- **WHEN** a backtest fails during execution
- **THEN** the task status SHALL transition: pending → running → failed, with error_message populated
