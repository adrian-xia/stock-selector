## ADDED Requirements

### Requirement: optimization_tasks table
The system SHALL provide an `optimization_tasks` database table with the following columns:

- `id` (int, PK, autoincrement)
- `strategy_name` (str, not null)
- `algorithm` (str, not null) — "grid" or "genetic"
- `param_space` (JSONB, not null) — parameter space definition
- `stock_codes` (JSONB, not null)
- `start_date` (date, not null)
- `end_date` (date, not null)
- `initial_capital` (numeric(20,2), default 1000000)
- `ga_config` (JSONB, nullable) — genetic algorithm hyperparameters
- `top_n` (int, default 20)
- `status` (str, default "pending") — pending/running/completed/failed
- `progress` (int, default 0) — 0-100 percentage
- `total_combinations` (int, nullable)
- `completed_combinations` (int, default 0)
- `error_message` (text, nullable)
- `created_at` (datetime, server_default now)
- `updated_at` (datetime, server_default now, onupdate now)

#### Scenario: Create optimization task record
- **WHEN** a new optimization task is submitted
- **THEN** a row SHALL be inserted with status="pending" and progress=0

### Requirement: optimization_results table
The system SHALL provide an `optimization_results` database table with the following columns:

- `id` (int, PK, autoincrement)
- `task_id` (int, FK → optimization_tasks.id, not null)
- `rank` (int, not null) — 1-based ranking by sharpe_ratio
- `params` (JSONB, not null) — the parameter combination
- `sharpe_ratio` (numeric(10,4), nullable)
- `annual_return` (numeric(10,4), nullable)
- `max_drawdown` (numeric(10,4), nullable)
- `win_rate` (numeric(10,4), nullable)
- `total_trades` (int, nullable)
- `total_return` (numeric(10,4), nullable)
- `volatility` (numeric(10,4), nullable)
- `calmar_ratio` (numeric(10,4), nullable)
- `sortino_ratio` (numeric(10,4), nullable)
- `created_at` (datetime, server_default now)

#### Scenario: Save top N results
- **WHEN** optimization completes with top_n=20
- **THEN** the top 20 results SHALL be inserted into optimization_results with rank 1..20

### Requirement: Alembic migration
The system SHALL provide an Alembic migration that creates both `optimization_tasks` and `optimization_results` tables.

#### Scenario: Migration upgrade
- **WHEN** `alembic upgrade head` is executed
- **THEN** both tables SHALL be created

#### Scenario: Migration downgrade
- **WHEN** `alembic downgrade -1` is executed
- **THEN** both tables SHALL be dropped
