## ADDED Requirements

### Requirement: Interactive data initialization wizard
The system SHALL provide an interactive wizard script to guide users through initial data setup on first deployment.

The wizard SHALL:
- Detect if the database already has data
- Prompt user to select a data range (1 year / 3 years / custom range)
- Execute the initialization steps in order: stock list → trade calendar → daily data → technical indicators
- Display progress for each step with estimated remaining time
- Provide confirmation prompts before overwriting existing data

#### Scenario: First-time initialization
- **WHEN** user runs `python scripts/init_data.py` on a fresh database
- **THEN** the wizard SHALL guide through data range selection and initialize all data

#### Scenario: Database already has data
- **WHEN** user runs the wizard and the database already contains data
- **THEN** it SHALL display a warning and prompt for confirmation before proceeding

#### Scenario: Select 1-year data range
- **WHEN** user selects "1 year" option
- **THEN** the wizard SHALL initialize data for the most recent 1 year (approximately 250 trading days)

#### Scenario: Select 3-year data range
- **WHEN** user selects "3 years" option
- **THEN** the wizard SHALL initialize data for the most recent 3 years (approximately 750 trading days)

#### Scenario: Custom date range
- **WHEN** user selects "custom range" option
- **THEN** the wizard SHALL prompt for start and end dates and initialize data for that range

### Requirement: Initialization step execution
The wizard SHALL execute initialization steps in the correct order with proper error handling.

Initialization steps:
1. Sync stock list (all listed stocks)
2. Sync trade calendar (for the selected date range)
3. Sync daily data (for all stocks in the selected date range)
4. Compute technical indicators (for all synced daily data)

#### Scenario: Successful initialization
- **WHEN** all initialization steps complete successfully
- **THEN** the wizard SHALL log "数据初始化完成：股票列表 N 只，交易日历 M 天，日线数据 X 条，技术指标 Y 条"

#### Scenario: Step failure
- **WHEN** an initialization step fails (e.g., API timeout)
- **THEN** the wizard SHALL log the error and prompt user to retry or skip the step

#### Scenario: Partial completion
- **WHEN** user cancels the wizard mid-process
- **THEN** the wizard SHALL log which steps were completed and which are pending

### Requirement: Progress display
The wizard SHALL display detailed progress information during long-running operations.

#### Scenario: Daily data sync progress
- **WHEN** the wizard is syncing daily data for 8000+ stocks
- **THEN** it SHALL display progress every 1000 stocks (e.g., "已同步 3000/8000 只股票，预计剩余 15 分钟")

#### Scenario: Technical indicator progress
- **WHEN** the wizard is computing technical indicators
- **THEN** it SHALL display progress every 1000 stocks (e.g., "已计算 5000/8000 只股票，预计剩余 5 分钟")

### Requirement: Confirmation prompts
The wizard SHALL prompt for user confirmation before potentially destructive operations.

#### Scenario: Overwrite existing data
- **WHEN** the database already has data and user proceeds with initialization
- **THEN** the wizard SHALL display "警告：数据库已有数据，继续将可能覆盖现有数据。是否继续？(y/N)" and wait for confirmation

#### Scenario: Large data range
- **WHEN** user selects a custom range larger than 5 years
- **THEN** the wizard SHALL display "警告：数据范围较大（X 年），初始化可能需要数小时。是否继续？(y/N)" and wait for confirmation
