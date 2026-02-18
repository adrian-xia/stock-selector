## ADDED Requirements

### Requirement: Submit optimization task
The system SHALL provide `POST /api/v1/optimization/run` endpoint that accepts an optimization request and executes it.

Request body:
- `strategy_name: str` — strategy identifier
- `algorithm: str` — "grid" or "genetic"
- `param_space: dict` — parameter ranges (overrides strategy default param_space)
- `stock_codes: list[str]` — stock codes for backtesting
- `start_date: date`
- `end_date: date`
- `initial_capital: float` (default 1000000)
- `ga_config: dict | null` — genetic algorithm hyperparameters (optional)
- `top_n: int` (default 20) — number of top results to save

Response: `{task_id, status, error_message?}`

#### Scenario: Submit grid search task
- **WHEN** POST `/api/v1/optimization/run` with algorithm="grid"
- **THEN** it SHALL create an optimization_tasks record, execute the optimization, save top N results, and return task_id with status

#### Scenario: Submit genetic algorithm task
- **WHEN** POST `/api/v1/optimization/run` with algorithm="genetic"
- **THEN** it SHALL create an optimization_tasks record, execute the GA optimization, save top N results, and return task_id with status

#### Scenario: Invalid strategy name
- **WHEN** POST with unknown strategy_name
- **THEN** it SHALL return 400 with error message

#### Scenario: Param space too large
- **WHEN** grid search total combinations exceed 10000
- **THEN** it SHALL return 400 with error message suggesting genetic algorithm

### Requirement: Get optimization result
The system SHALL provide `GET /api/v1/optimization/result/{task_id}` endpoint.

Response: task info + list of optimization_results sorted by rank.

#### Scenario: Query completed task
- **WHEN** GET `/api/v1/optimization/result/{task_id}` for a completed task
- **THEN** it SHALL return task details and top N results with params and metrics

#### Scenario: Query non-existent task
- **WHEN** GET with non-existent task_id
- **THEN** it SHALL return 404

### Requirement: List optimization tasks
The system SHALL provide `GET /api/v1/optimization/list` endpoint with pagination.

Query params: `page` (default 1), `page_size` (default 20)

#### Scenario: Paginated list
- **WHEN** GET `/api/v1/optimization/list?page=1&page_size=10`
- **THEN** it SHALL return total count and paginated items sorted by created_at descending

### Requirement: Get strategy param space
The system SHALL provide `GET /api/v1/optimization/param-space/{strategy_name}` endpoint.

#### Scenario: Query param space
- **WHEN** GET `/api/v1/optimization/param-space/ma-cross`
- **THEN** it SHALL return the param_space definition for the strategy

#### Scenario: Strategy without param space
- **WHEN** GET for a strategy that has no param_space defined
- **THEN** it SHALL return 404 with message
