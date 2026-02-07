## ADDED Requirements

### Requirement: DataManager unified data access
The system SHALL provide a `DataManager` class that serves as the single entry point for all data access operations. It SHALL encapsulate data source clients, ETL logic, and database queries behind a clean async API.

The `DataManager` SHALL be initialized with:
- A database async session factory
- Configured data source clients (BaoStockClient, AKShareClient)
- A primary source setting (default: `"baostock"`)

#### Scenario: DataManager initialization
- **WHEN** the application starts
- **THEN** a `DataManager` instance SHALL be created with all configured data source clients
- **AND** the primary source SHALL be set according to configuration

### Requirement: get_daily_bars query interface
The `DataManager` SHALL provide `get_daily_bars()` for retrieving standardized daily bar data from the database with optional forward/backward adjustment.

Signature:
```python
async def get_daily_bars(
    codes: list[str],
    start_date: date,
    end_date: date,
    adj: str = "qfq",
    fields: list[str] | None = None,
) -> pd.DataFrame
```

Adjustment calculation:
- Forward adjust (qfq): `adjusted_price = raw_price * adj_factor / latest_adj_factor`
- Backward adjust (hfq): `adjusted_price = raw_price * adj_factor`
- No adjust (none): return raw prices

#### Scenario: Query single stock with forward adjustment
- **WHEN** `get_daily_bars(["600519.SH"], date(2025,1,1), date(2025,12,31), adj="qfq")` is called
- **THEN** it SHALL return a DataFrame with columns: `ts_code`, `trade_date`, `open`, `high`, `low`, `close`, `vol`, `amount`, `pct_chg`, `turnover_rate`
- **AND** price columns SHALL be forward-adjusted using the adj_factor

#### Scenario: Query multiple stocks
- **WHEN** `get_daily_bars(["600519.SH", "000001.SZ"], ...)` is called
- **THEN** the result DataFrame SHALL contain data for both stocks, sorted by `(ts_code, trade_date)`

#### Scenario: No data found
- **WHEN** `get_daily_bars()` is called with a code or date range that has no data
- **THEN** it SHALL return an empty DataFrame with the correct column schema

### Requirement: get_stock_list query interface
The `DataManager` SHALL provide `get_stock_list()` for retrieving the current list of A-share stocks from the database.

#### Scenario: Retrieve active stock list
- **WHEN** `get_stock_list(status="L")` is called
- **THEN** it SHALL return a list of dicts with keys: `ts_code`, `name`, `industry`, `market`, `list_date`, `list_status`
- **AND** only stocks with `list_status = 'L'` (listed) SHALL be included

### Requirement: get_trade_calendar query interface
The `DataManager` SHALL provide `get_trade_calendar()` for retrieving trading dates.

#### Scenario: Retrieve trading days in a range
- **WHEN** `get_trade_calendar(date(2025,1,1), date(2025,12,31))` is called
- **THEN** it SHALL return a sorted list of `date` objects representing trading days (where `is_open = True`)

#### Scenario: Check if a specific date is a trading day
- **WHEN** `is_trade_day(date(2025, 10, 1))` is called (National Day holiday)
- **THEN** it SHALL return `False`

### Requirement: sync_daily data synchronization
The `DataManager` SHALL provide `sync_daily()` for fetching and persisting daily bar data from the primary data source.

The method SHALL:
1. Fetch data from the primary source client
2. Run ETL cleaning on the raw data
3. Batch insert into `stock_daily`
4. Return a summary dict with counts of inserted/skipped/failed records

#### Scenario: Successful daily sync for all stocks
- **WHEN** `sync_daily(trade_date=date(2025, 6, 15))` is called on a trading day
- **THEN** it SHALL fetch daily data for all listed stocks from the primary source
- **AND** clean and insert the data into `stock_daily`
- **AND** return `{"inserted": N, "skipped": M, "failed": 0}`

#### Scenario: Sync on non-trading day
- **WHEN** `sync_daily()` is called and today is not a trading day
- **THEN** it SHALL skip the sync and return `{"skipped": "non-trading day"}`

### Requirement: sync_stock_list stock list synchronization
The `DataManager` SHALL provide `sync_stock_list()` for updating the `stocks` table with the latest stock list from the data source.

#### Scenario: New stock IPO detected
- **WHEN** `sync_stock_list()` is called and a new stock has been listed since the last sync
- **THEN** the new stock SHALL be inserted into the `stocks` table
- **AND** existing stocks SHALL have their `list_status` updated if changed (e.g., delisted)

### Requirement: sync_trade_calendar calendar synchronization
The `DataManager` SHALL provide `sync_trade_calendar()` for updating the `trade_calendar` table.

#### Scenario: Calendar sync
- **WHEN** `sync_trade_calendar(year=2026)` is called
- **THEN** all trading days and holidays for 2026 SHALL be inserted/updated in `trade_calendar`

### Requirement: Primary source fallback on failure
In V1, when the primary data source fails, the `DataManager` SHALL log an error and attempt the same operation with the backup source. This is a simple fallback, not a full state machine.

#### Scenario: Primary source fails, backup succeeds
- **WHEN** the primary source (BaoStock) raises a `DataSourceError` during `sync_daily()`
- **THEN** the `DataManager` SHALL log a warning
- **AND** retry the operation using the backup source (AKShare)
- **AND** tag the resulting records with `data_source = "akshare"`

#### Scenario: Both sources fail
- **WHEN** both primary and backup sources fail
- **THEN** the `DataManager` SHALL log an error with details from both failures
- **AND** raise a `DataSyncError`

### Requirement: get_latest_technical query interface
The `DataManager` SHALL provide a `get_latest_technical()` method for retrieving the most recent technical indicators for given stocks from the `technical_daily` table.

Signature:
```python
async def get_latest_technical(
    self,
    codes: list[str],
    trade_date: date | None = None,
    fields: list[str] | None = None,
) -> pd.DataFrame
```

- If `trade_date` is provided, return indicators for that specific date
- If `trade_date` is None, return the most recent available indicators for each stock
- If `fields` is provided, return only the specified indicator columns (plus `ts_code` and `trade_date`)
- If `fields` is None, return all indicator columns

#### Scenario: Query latest indicators for multiple stocks
- **WHEN** `get_latest_technical(["600519.SH", "000001.SZ"])` is called
- **THEN** it SHALL return a DataFrame with the most recent technical indicators for both stocks
- **AND** the DataFrame SHALL contain columns: `ts_code`, `trade_date`, `ma5`, `ma10`, `ma20`, `ma60`, `ma120`, `ma250`, `macd_dif`, `macd_dea`, `macd_hist`, `kdj_k`, `kdj_d`, `kdj_j`, `rsi6`, `rsi12`, `rsi24`, `boll_upper`, `boll_mid`, `boll_lower`, `vol_ma5`, `vol_ma10`, `vol_ratio`, `atr14`

#### Scenario: Query indicators for a specific date
- **WHEN** `get_latest_technical(["600519.SH"], trade_date=date(2026, 2, 7))` is called
- **THEN** it SHALL return indicators computed for 2026-02-07 specifically
- **AND** if no data exists for that date, return an empty DataFrame

#### Scenario: Query with field selection
- **WHEN** `get_latest_technical(["600519.SH"], fields=["ma5", "ma10", "rsi6"])` is called
- **THEN** the returned DataFrame SHALL contain only `ts_code`, `trade_date`, `ma5`, `ma10`, `rsi6` columns

#### Scenario: No indicators available
- **WHEN** `get_latest_technical(["999999.SH"])` is called for a stock with no computed indicators
- **THEN** it SHALL return an empty DataFrame with the correct column schema
