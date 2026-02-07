## ADDED Requirements

### Requirement: DataSourceClient abstract interface
The system SHALL define a `DataSourceClient` Protocol (or ABC) with the following async methods:
- `fetch_daily(code: str, start_date: date, end_date: date) -> list[dict]`
- `fetch_stock_list() -> list[dict]`
- `fetch_trade_calendar(start_date: date, end_date: date) -> list[dict]`
- `health_check() -> bool`

All data source implementations SHALL conform to this interface.

#### Scenario: Interface contract enforcement
- **WHEN** a new data source client class is created
- **THEN** it SHALL implement all methods defined in `DataSourceClient`

#### Scenario: Health check returns boolean
- **WHEN** `health_check()` is called on any client
- **THEN** it SHALL return `True` if the data source is reachable and `False` otherwise, without raising exceptions

### Requirement: BaoStock client implementation
The system SHALL provide a `BaoStockClient` that implements `DataSourceClient` for fetching historical daily bars, stock lists, and trade calendars from BaoStock.

The client SHALL:
- Call `baostock.login()` before any data request and `baostock.logout()` after
- Convert BaoStock stock codes (e.g., `sh.600519`) to standard format (`600519.SH`) in the returned data
- Support fetching daily OHLCV data with adjustflag=3 (unadjusted) by default
- Handle BaoStock's synchronous API by running it in a thread executor to avoid blocking the async event loop

#### Scenario: Fetch daily bars for a single stock
- **WHEN** `fetch_daily("600519.SH", date(2025, 1, 1), date(2025, 12, 31))` is called
- **THEN** the client SHALL return a list of dicts, each containing keys: `ts_code`, `trade_date`, `open`, `high`, `low`, `close`, `pre_close`, `vol`, `amount`, `pct_chg`, `turn`, `trade_status`, `is_st`
- **AND** all numeric values SHALL be converted from strings to appropriate Python types (`Decimal` for prices, `float` for percentages)

#### Scenario: Fetch stock list
- **WHEN** `fetch_stock_list()` is called
- **THEN** the client SHALL return all A-share stocks with fields: `ts_code`, `name`, `industry`, `area`, `market`, `list_date`, `list_status`

#### Scenario: BaoStock login failure
- **WHEN** BaoStock login fails (network error or credential issue)
- **THEN** the client SHALL raise a `DataSourceError` with a descriptive message
- **AND** SHALL NOT leave the BaoStock session in an inconsistent state

#### Scenario: Fetch trade calendar
- **WHEN** `fetch_trade_calendar(date(2025, 1, 1), date(2025, 12, 31))` is called
- **THEN** the client SHALL return a list of dicts with keys: `cal_date`, `is_open` (bool)

### Requirement: AKShare client implementation
The system SHALL provide an `AKShareClient` that implements `DataSourceClient` as a backup data source. V1 scope focuses on daily bars and stock list retrieval.

The client SHALL:
- Use AKShare's `stock_zh_a_hist` for historical daily data
- Convert AKShare's Chinese column names to standard English field names
- Convert AKShare's 6-digit codes to standard format by detecting exchange from code prefix

#### Scenario: Fetch daily bars via AKShare
- **WHEN** `fetch_daily("600519.SH", date(2025, 1, 1), date(2025, 12, 31))` is called on `AKShareClient`
- **THEN** the client SHALL return data in the same dict format as `BaoStockClient`
- **AND** Chinese column names (日期, 开盘, 收盘, etc.) SHALL be mapped to standard names

#### Scenario: AKShare API timeout
- **WHEN** an AKShare API call exceeds the configured timeout
- **THEN** the client SHALL raise a `DataSourceError` after exhausting retry attempts

### Requirement: Retry with exponential backoff
Each data source client SHALL implement automatic retry with exponential backoff for transient failures (network timeouts, HTTP 5xx errors).

Configuration SHALL be read from app settings:
- `retry_count`: max number of retries (default: 3)
- `retry_interval`: base interval in seconds (default: 2.0)

The backoff formula SHALL be: `retry_interval * (2 ** attempt_number)`.

#### Scenario: Transient failure with successful retry
- **WHEN** a data source API call fails with a network timeout on the first attempt
- **AND** succeeds on the second attempt
- **THEN** the client SHALL return the data from the successful attempt
- **AND** SHALL log a warning about the retry

#### Scenario: All retries exhausted
- **WHEN** a data source API call fails on all retry attempts
- **THEN** the client SHALL raise a `DataSourceError` containing the last error message and the number of attempts made

### Requirement: QPS rate limiting
Each data source client SHALL enforce a per-second (or per-minute for Tushare) request rate limit to avoid being blocked by the data source.

The rate limiter SHALL use an async semaphore or token bucket approach.

#### Scenario: Requests within QPS limit
- **WHEN** requests are made at a rate below the configured `qps_limit`
- **THEN** all requests SHALL proceed without delay

#### Scenario: Requests exceeding QPS limit
- **WHEN** requests are made at a rate exceeding the configured `qps_limit`
- **THEN** excess requests SHALL be delayed (not rejected) until a slot becomes available
