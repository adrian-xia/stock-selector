## MODIFIED Requirements

### Requirement: DataSourceClient abstract interface
The system SHALL define a `DataSourceClient` Protocol (or ABC) with the following async methods:
- `fetch_daily(code: str, start_date: date, end_date: date) -> list[dict]`
- `fetch_stock_list() -> list[dict]`
- `fetch_trade_calendar(start_date: date, end_date: date) -> list[dict]`
- `fetch_adj_factor(code: str, start_date: date, end_date: date) -> list[dict]`
- `health_check() -> bool`

All data source implementations SHALL conform to this interface.

#### Scenario: Interface contract enforcement
- **WHEN** a new data source client class is created
- **THEN** it SHALL implement all methods defined in `DataSourceClient`

#### Scenario: Health check returns boolean
- **WHEN** `health_check()` is called on any client
- **THEN** it SHALL return `True` if the data source is reachable and `False` otherwise, without raising exceptions

### Requirement: BaoStock client implementation
The system SHALL provide a `BaoStockClient` that implements `DataSourceClient` for fetching historical daily bars, stock lists, trade calendars, and adjustment factors from BaoStock.

The client SHALL:
- Call `baostock.login()` before any data request and `baostock.logout()` after
- Convert BaoStock stock codes (e.g., `sh.600519`) to standard format (`600519.SH`) in the returned data
- Support fetching daily OHLCV data with adjustflag=3 (unadjusted) by default
- Support fetching adjustment factors via `bs.query_adjust_factor()`
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

#### Scenario: Fetch adjustment factors
- **WHEN** `fetch_adj_factor("600519.SH", date(2025, 1, 1), date(2025, 12, 31))` is called
- **THEN** the client SHALL return a list of dicts with keys: `ts_code` (str), `trade_date` (str), `adj_factor` (Decimal)
- **AND** the `adj_factor` value SHALL be sourced from BaoStock's `foreAdjustFactor` field
