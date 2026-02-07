## ADDED Requirements

### Requirement: trade_calendar table
The system SHALL create a `trade_calendar` table storing trading day information for Chinese stock exchanges.

DDL:
```sql
CREATE TABLE trade_calendar (
    cal_date    DATE        NOT NULL,
    exchange    VARCHAR(10) NOT NULL DEFAULT 'SSE',
    is_open     BOOLEAN     NOT NULL DEFAULT FALSE,
    pre_trade_date DATE,
    CONSTRAINT pk_trade_calendar PRIMARY KEY (cal_date, exchange)
);
```

#### Scenario: Query trading days in a range
- **WHEN** `SELECT cal_date FROM trade_calendar WHERE is_open = TRUE AND cal_date BETWEEN '2025-01-01' AND '2025-12-31' ORDER BY cal_date` is executed
- **THEN** it SHALL return all trading days in 2025

### Requirement: stocks table
The system SHALL create a `stocks` table storing basic information for all A-share stocks.

DDL:
```sql
CREATE TABLE stocks (
    ts_code     VARCHAR(16)  NOT NULL PRIMARY KEY,
    symbol      VARCHAR(10),
    name        VARCHAR(32)  NOT NULL,
    area        VARCHAR(20),
    industry    VARCHAR(50),
    market      VARCHAR(16),
    list_date   DATE,
    list_status VARCHAR(4)   NOT NULL DEFAULT 'L',
    is_hs       VARCHAR(4),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
```

#### Scenario: Query listed stocks
- **WHEN** `SELECT ts_code, name FROM stocks WHERE list_status = 'L'` is executed
- **THEN** it SHALL return all currently listed A-share stocks

### Requirement: stock_daily table
The system SHALL create a `stock_daily` table storing daily OHLCV bar data with adjustment factors.

DDL:
```sql
CREATE TABLE stock_daily (
    ts_code       VARCHAR(16)    NOT NULL,
    trade_date    DATE           NOT NULL,
    open          DECIMAL(10,2)  NOT NULL,
    high          DECIMAL(10,2)  NOT NULL,
    low           DECIMAL(10,2)  NOT NULL,
    close         DECIMAL(10,2)  NOT NULL,
    pre_close     DECIMAL(10,2),
    pct_chg       DECIMAL(10,4),
    vol           DECIMAL(20,2)  NOT NULL DEFAULT 0,
    amount        DECIMAL(20,2)  NOT NULL DEFAULT 0,
    adj_factor    DECIMAL(16,6),
    turnover_rate DECIMAL(10,4),
    trade_status  VARCHAR(4)     NOT NULL DEFAULT '1',
    data_source   VARCHAR(16)    NOT NULL DEFAULT 'baostock',
    created_at    TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP      NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stock_daily PRIMARY KEY (ts_code, trade_date)
);

CREATE INDEX idx_stock_daily_code_date ON stock_daily (ts_code, trade_date DESC);
CREATE INDEX idx_stock_daily_trade_date ON stock_daily (trade_date);
```

#### Scenario: Insert daily bar data
- **WHEN** a cleaned daily bar record is inserted
- **THEN** it SHALL be stored with the composite primary key `(ts_code, trade_date)`
- **AND** duplicate inserts (same ts_code + trade_date) SHALL be rejected by the PK constraint

### Requirement: stock_min table
The system SHALL create a `stock_min` table for minute-level bar data. V1 uses a plain PostgreSQL table (no TimescaleDB).

DDL:
```sql
CREATE TABLE stock_min (
    ts_code     VARCHAR(16)    NOT NULL,
    trade_time  TIMESTAMP      NOT NULL,
    freq        VARCHAR(8)     NOT NULL DEFAULT '5min',
    open        DECIMAL(10,2)  NOT NULL,
    high        DECIMAL(10,2)  NOT NULL,
    low         DECIMAL(10,2)  NOT NULL,
    close       DECIMAL(10,2)  NOT NULL,
    vol         DECIMAL(20,2)  NOT NULL DEFAULT 0,
    amount      DECIMAL(20,2)  NOT NULL DEFAULT 0,
    data_source VARCHAR(16)    NOT NULL DEFAULT 'baostock',
    created_at  TIMESTAMP      NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stock_min PRIMARY KEY (ts_code, trade_time, freq)
);

CREATE INDEX idx_stock_min_code_time ON stock_min (ts_code, trade_time DESC);
```

#### Scenario: Query 5-minute bars for a stock
- **WHEN** `SELECT * FROM stock_min WHERE ts_code = '600519.SH' AND freq = '5min' AND trade_time BETWEEN ... ORDER BY trade_time` is executed
- **THEN** it SHALL return 5-minute OHLCV bars in chronological order

### Requirement: finance_indicator table
The system SHALL create a `finance_indicator` table storing key financial metrics per reporting period.

DDL:
```sql
CREATE TABLE finance_indicator (
    ts_code       VARCHAR(16)    NOT NULL,
    ann_date      DATE,
    end_date      DATE           NOT NULL,
    report_type   VARCHAR(8)     NOT NULL DEFAULT 'Q',
    eps           DECIMAL(10,4),
    roe           DECIMAL(10,4),
    roe_diluted   DECIMAL(10,4),
    gross_margin  DECIMAL(10,4),
    net_margin    DECIMAL(10,4),
    revenue_yoy   DECIMAL(10,4),
    profit_yoy    DECIMAL(10,4),
    pe_ttm        DECIMAL(12,4),
    pb            DECIMAL(10,4),
    ps_ttm        DECIMAL(10,4),
    total_mv      DECIMAL(20,2),
    circ_mv       DECIMAL(20,2),
    current_ratio DECIMAL(10,4),
    quick_ratio   DECIMAL(10,4),
    debt_ratio    DECIMAL(10,4),
    ocf_per_share DECIMAL(10,4),
    data_source   VARCHAR(16)    NOT NULL DEFAULT 'baostock',
    created_at    TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP      NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_finance_indicator PRIMARY KEY (ts_code, end_date, report_type)
);

CREATE INDEX idx_finance_code_date ON finance_indicator (ts_code, end_date DESC);
CREATE INDEX idx_finance_end_date ON finance_indicator (end_date);
CREATE INDEX idx_finance_ann_date ON finance_indicator (ann_date);
```

#### Scenario: Query latest financial data for a stock
- **WHEN** `SELECT * FROM finance_indicator WHERE ts_code = '600519.SH' ORDER BY end_date DESC LIMIT 1` is executed
- **THEN** it SHALL return the most recent financial report data

### Requirement: technical_daily table
The system SHALL create a `technical_daily` table for caching pre-computed daily technical indicators.

DDL:
```sql
CREATE TABLE technical_daily (
    ts_code     VARCHAR(16)    NOT NULL,
    trade_date  DATE           NOT NULL,
    ma5         DECIMAL(10,2),
    ma10        DECIMAL(10,2),
    ma20        DECIMAL(10,2),
    ma60        DECIMAL(10,2),
    ma120       DECIMAL(10,2),
    ma250       DECIMAL(10,2),
    macd_dif    DECIMAL(10,4),
    macd_dea    DECIMAL(10,4),
    macd_hist   DECIMAL(10,4),
    kdj_k       DECIMAL(10,4),
    kdj_d       DECIMAL(10,4),
    kdj_j       DECIMAL(10,4),
    rsi6        DECIMAL(10,4),
    rsi12       DECIMAL(10,4),
    rsi24       DECIMAL(10,4),
    boll_upper  DECIMAL(10,2),
    boll_mid    DECIMAL(10,2),
    boll_lower  DECIMAL(10,2),
    vol_ma5     DECIMAL(20,2),
    vol_ma10    DECIMAL(20,2),
    vol_ratio   DECIMAL(10,4),
    atr14       DECIMAL(10,4),
    created_at  TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP      NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_technical_daily PRIMARY KEY (ts_code, trade_date)
);

CREATE INDEX idx_technical_code_date ON technical_daily (ts_code, trade_date DESC);
CREATE INDEX idx_technical_trade_date ON technical_daily (trade_date);
```

#### Scenario: Query latest technical indicators
- **WHEN** `SELECT * FROM technical_daily WHERE ts_code = '600519.SH' ORDER BY trade_date DESC LIMIT 1` is executed
- **THEN** it SHALL return the most recently computed technical indicators for that stock

### Requirement: money_flow table
The system SHALL create a `money_flow` table for individual stock capital flow data.

DDL:
```sql
CREATE TABLE money_flow (
    ts_code         VARCHAR(16)    NOT NULL,
    trade_date      DATE           NOT NULL,
    buy_sm_vol      DECIMAL(20,2)  DEFAULT 0,
    buy_sm_amount   DECIMAL(20,2)  DEFAULT 0,
    sell_sm_vol     DECIMAL(20,2)  DEFAULT 0,
    sell_sm_amount  DECIMAL(20,2)  DEFAULT 0,
    buy_md_vol      DECIMAL(20,2)  DEFAULT 0,
    buy_md_amount   DECIMAL(20,2)  DEFAULT 0,
    sell_md_vol     DECIMAL(20,2)  DEFAULT 0,
    sell_md_amount  DECIMAL(20,2)  DEFAULT 0,
    buy_lg_vol      DECIMAL(20,2)  DEFAULT 0,
    buy_lg_amount   DECIMAL(20,2)  DEFAULT 0,
    sell_lg_vol     DECIMAL(20,2)  DEFAULT 0,
    sell_lg_amount  DECIMAL(20,2)  DEFAULT 0,
    buy_elg_vol     DECIMAL(20,2)  DEFAULT 0,
    buy_elg_amount  DECIMAL(20,2)  DEFAULT 0,
    sell_elg_vol    DECIMAL(20,2)  DEFAULT 0,
    sell_elg_amount DECIMAL(20,2)  DEFAULT 0,
    net_mf_amount   DECIMAL(20,2)  DEFAULT 0,
    data_source     VARCHAR(16)    NOT NULL DEFAULT 'akshare',
    created_at      TIMESTAMP      NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_money_flow PRIMARY KEY (ts_code, trade_date)
);
```

#### Scenario: Query net capital flow
- **WHEN** `SELECT ts_code, net_mf_amount FROM money_flow WHERE trade_date = '2025-06-15' ORDER BY net_mf_amount DESC LIMIT 10` is executed
- **THEN** it SHALL return the top 10 stocks by net capital inflow for that date

### Requirement: dragon_tiger table
The system SHALL create a `dragon_tiger` table for storing top buyer/seller list data.

DDL:
```sql
CREATE TABLE dragon_tiger (
    id          SERIAL         PRIMARY KEY,
    ts_code     VARCHAR(16)    NOT NULL,
    trade_date  DATE           NOT NULL,
    reason      VARCHAR(200),
    buy_total   DECIMAL(20,2),
    sell_total  DECIMAL(20,2),
    net_buy     DECIMAL(20,2),
    list_name   VARCHAR(100),
    data_source VARCHAR(16)    NOT NULL DEFAULT 'akshare',
    created_at  TIMESTAMP      NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dragon_tiger_date ON dragon_tiger (trade_date);
CREATE INDEX idx_dragon_tiger_code ON dragon_tiger (ts_code, trade_date DESC);
```

#### Scenario: Query dragon tiger list for a date
- **WHEN** `SELECT * FROM dragon_tiger WHERE trade_date = '2025-06-15'` is executed
- **THEN** it SHALL return all dragon tiger list entries for that trading day

### Requirement: strategies table
The system SHALL create a `strategies` table for storing strategy configurations.

DDL:
```sql
CREATE TABLE strategies (
    id          SERIAL         PRIMARY KEY,
    name        VARCHAR(64)    NOT NULL UNIQUE,
    category    VARCHAR(32)    NOT NULL,
    description TEXT,
    params      JSONB          NOT NULL DEFAULT '{}',
    is_enabled  BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP      NOT NULL DEFAULT NOW()
);
```

#### Scenario: Query enabled strategies
- **WHEN** `SELECT * FROM strategies WHERE is_enabled = TRUE` is executed
- **THEN** it SHALL return all active strategy configurations

### Requirement: data_source_configs table
The system SHALL create a `data_source_configs` table for managing data source connection settings.

DDL:
```sql
CREATE TABLE data_source_configs (
    id              SERIAL         PRIMARY KEY,
    source_name     VARCHAR(32)    NOT NULL UNIQUE,
    priority        INTEGER        NOT NULL DEFAULT 1,
    is_enabled      BOOLEAN        NOT NULL DEFAULT TRUE,
    config          JSONB          NOT NULL DEFAULT '{}',
    last_health_check TIMESTAMP,
    created_at      TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP      NOT NULL DEFAULT NOW()
);
```

#### Scenario: Query active data sources by priority
- **WHEN** `SELECT * FROM data_source_configs WHERE is_enabled = TRUE ORDER BY priority` is executed
- **THEN** it SHALL return data sources ordered by priority (lower number = higher priority)

### Requirement: backtest_tasks table
The system SHALL create a `backtest_tasks` table for tracking backtest job submissions.

DDL:
```sql
CREATE TABLE backtest_tasks (
    id              SERIAL         PRIMARY KEY,
    strategy_id     INTEGER        REFERENCES strategies(id),
    strategy_params JSONB          NOT NULL DEFAULT '{}',
    stock_codes     JSONB          NOT NULL DEFAULT '[]',
    start_date      DATE           NOT NULL,
    end_date        DATE           NOT NULL,
    initial_capital DECIMAL(20,2)  NOT NULL DEFAULT 1000000,
    status          VARCHAR(16)    NOT NULL DEFAULT 'pending',
    error_message   TEXT,
    created_at      TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP      NOT NULL DEFAULT NOW()
);
```

#### Scenario: Submit a backtest task
- **WHEN** a new backtest task is inserted with `status = 'pending'`
- **THEN** it SHALL be persisted and retrievable by its auto-generated `id`

### Requirement: backtest_results table
The system SHALL create a `backtest_results` table storing backtest outcomes with trades and equity curve as JSONB fields (V1 simplified).

DDL:
```sql
CREATE TABLE backtest_results (
    id                  SERIAL         PRIMARY KEY,
    task_id             INTEGER        NOT NULL REFERENCES backtest_tasks(id),
    total_return        DECIMAL(10,4),
    annual_return       DECIMAL(10,4),
    max_drawdown        DECIMAL(10,4),
    sharpe_ratio        DECIMAL(10,4),
    win_rate            DECIMAL(10,4),
    profit_loss_ratio   DECIMAL(10,4),
    total_trades        INTEGER,
    benchmark_return    DECIMAL(10,4),
    alpha               DECIMAL(10,4),
    beta                DECIMAL(10,4),
    volatility          DECIMAL(10,4),
    calmar_ratio        DECIMAL(10,4),
    sortino_ratio       DECIMAL(10,4),
    trades_json         JSONB          NOT NULL DEFAULT '[]',
    equity_curve_json   JSONB          NOT NULL DEFAULT '[]',
    created_at          TIMESTAMP      NOT NULL DEFAULT NOW()
);
```

#### Scenario: Store backtest result
- **WHEN** a backtest completes successfully
- **THEN** the result SHALL be inserted with all performance metrics and the full trade list and equity curve as JSONB
