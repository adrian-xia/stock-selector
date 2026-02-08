## MODIFIED Requirements

### Requirement: BaoStock client implementation
The system SHALL provide a `BaoStockClient` that implements `DataSourceClient` for fetching historical daily bars, stock lists, trade calendars, and adjustment factors from BaoStock.

The client SHALL:
- Use a connection pool to reuse BaoStock login sessions instead of calling `login()` and `logout()` for each request
- Convert BaoStock stock codes (e.g., `sh.600519`) to standard format (`600519.SH`) in the returned data
- Support fetching daily OHLCV data with adjustflag=3 (unadjusted) by default
- Support fetching adjustment factors via `bs.query_adjust_factor()`
- Handle BaoStock's synchronous API by running it in a thread executor to avoid blocking the async event loop
- Accept an optional `connection_pool` parameter in the constructor for connection reuse

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

#### Scenario: Fetch adjustment factors
- **WHEN** `fetch_adj_factor("600519.SH", date(2025, 1, 1), date(2025, 12, 31))` is called
- **THEN** the client SHALL return a list of dicts with keys: `ts_code` (str), `trade_date` (str), `adj_factor` (Decimal)
- **AND** the `adj_factor` value SHALL be sourced from BaoStock's `foreAdjustFactor` field

#### Scenario: Use connection pool when provided
- **WHEN** `BaoStockClient(connection_pool=pool)` is instantiated with a connection pool
- **THEN** all data fetch operations SHALL acquire connections from the pool instead of calling `bs.login()` directly

#### Scenario: Fallback to direct login when no pool
- **WHEN** `BaoStockClient()` is instantiated without a connection pool
- **THEN** it SHALL use the legacy behavior of calling `bs.login()` and `bs.logout()` for each request

#### Scenario: Connection acquired from pool
- **WHEN** a fetch operation needs to query BaoStock and a connection pool is configured
- **THEN** the client SHALL call `pool.acquire()` to get a logged-in session, use it for the query, and call `pool.release()` when done

## ADDED Requirements

### Requirement: Batch fetch support
The `BaoStockClient` SHALL provide a `batch_fetch_daily()` method that fetches daily data for multiple stocks concurrently using the connection pool.

#### Scenario: Batch fetch multiple stocks
- **WHEN** `batch_fetch_daily(["600519.SH", "000001.SZ"], date(2025, 1, 1), date(2025, 1, 31))` is called
- **THEN** the client SHALL fetch data for both stocks concurrently and return a dict mapping stock codes to their data lists

#### Scenario: Batch fetch with connection pool
- **WHEN** `batch_fetch_daily()` is called with a connection pool configured
- **THEN** it SHALL reuse connections from the pool for concurrent fetches

#### Scenario: Batch fetch handles individual failures
- **WHEN** one stock in the batch fails to fetch (e.g., invalid code)
- **THEN** the client SHALL continue fetching remaining stocks and include the error in the result dict
