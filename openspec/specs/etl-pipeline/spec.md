## ADDED Requirements

### Requirement: Stock code standardization
The ETL pipeline SHALL normalize stock codes from all data sources into the standard format `{6-digit code}.{SH|SZ|BJ}`.

Mapping rules:
- BaoStock `sh.600519` → `600519.SH`
- BaoStock `sz.000001` → `000001.SZ`
- AKShare `600519` → `600519.SH` (detect exchange from prefix: 6xx=SH, 0xx/3xx=SZ, 8xx/4xx=BJ)

#### Scenario: BaoStock code normalization
- **WHEN** a raw record with code `sh.600519` is processed
- **THEN** the output `ts_code` field SHALL be `600519.SH`

#### Scenario: AKShare code normalization
- **WHEN** a raw record with code `000001` is processed
- **THEN** the output `ts_code` field SHALL be `000001.SZ`

#### Scenario: Beijing exchange code normalization
- **WHEN** a raw record with code `830799` (8xx prefix) is processed
- **THEN** the output `ts_code` field SHALL be `830799.BJ`

### Requirement: Numeric type conversion
The ETL pipeline SHALL convert string values from data source APIs into proper numeric types with defined precision.

Conversion rules:
- Prices (open, high, low, close, pre_close): `Decimal(10, 2)`
- Percentages (pct_chg, turnover_rate): `Decimal(10, 4)`
- Volume (vol): `Decimal(20, 2)` in units of 手 (lots)
- Amount (amount): `Decimal(20, 2)` in units of 千元 (thousands of yuan)

#### Scenario: Valid numeric conversion
- **WHEN** a raw price string `"1705.20"` is processed
- **THEN** it SHALL be converted to `Decimal("1705.20")`

#### Scenario: Empty or null value handling
- **WHEN** a raw value is `""`, `"N/A"`, `"--"`, `"None"`, or `None`
- **THEN** it SHALL be converted to `None` (SQL NULL)
- **AND** SHALL NOT raise an exception

#### Scenario: Non-numeric value in numeric field
- **WHEN** a raw value contains unexpected non-numeric content (e.g., `"error"`)
- **THEN** it SHALL be converted to `None`
- **AND** a warning SHALL be logged with the field name, raw value, and stock code

### Requirement: Date format standardization
The ETL pipeline SHALL normalize date strings from all sources into Python `date` objects.

Supported input formats:
- `"2025-01-15"` (BaoStock)
- `"20250115"` (Tushare-style)

#### Scenario: Hyphenated date parsing
- **WHEN** a raw date string `"2025-01-15"` is processed
- **THEN** it SHALL be converted to `date(2025, 1, 15)`

#### Scenario: Compact date parsing
- **WHEN** a raw date string `"20250115"` is processed
- **THEN** it SHALL be converted to `date(2025, 1, 15)`

### Requirement: Trade status normalization
The ETL pipeline SHALL normalize trade status values to a standard format: `"1"` for normal trading, `"0"` for suspended.

#### Scenario: BaoStock trade status
- **WHEN** BaoStock returns `tradestatus = "1"`
- **THEN** the output `trade_status` field SHALL be `"1"`

#### Scenario: Suspended stock detection
- **WHEN** a stock has zero volume and zero amount on a trading day
- **THEN** the `trade_status` field SHALL be set to `"0"` regardless of the source value

### Requirement: Data source tagging
The ETL pipeline SHALL tag each output record with a `data_source` field indicating which source provided the data (e.g., `"baostock"`, `"akshare"`).

#### Scenario: BaoStock sourced record
- **WHEN** a record is cleaned from BaoStock raw data
- **THEN** the `data_source` field SHALL be `"baostock"`

#### Scenario: AKShare sourced record
- **WHEN** a record is cleaned from AKShare raw data
- **THEN** the `data_source` field SHALL be `"akshare"`

### Requirement: ETL batch processing
The ETL pipeline SHALL process records in batches for database insertion efficiency. Each batch SHALL use `INSERT ... ON CONFLICT DO NOTHING` to handle duplicate records gracefully.

The batch size SHALL be configurable via `etl.batch_size` (default: 5000).

#### Scenario: Batch insert with no conflicts
- **WHEN** a batch of 5000 cleaned records is inserted into `stock_daily`
- **THEN** all 5000 records SHALL be persisted in a single database round-trip

#### Scenario: Batch insert with duplicate records
- **WHEN** a batch contains records that already exist in the target table (same `ts_code` + `trade_date`)
- **THEN** existing records SHALL NOT be overwritten
- **AND** new records SHALL be inserted
- **AND** no error SHALL be raised

### Requirement: Direct ETL without raw layer
In V1, the ETL pipeline SHALL clean and insert data directly into standard tables (`stock_daily`, `stocks`, `trade_calendar`, `finance_indicator`) without an intermediate raw layer. Data source API responses are cleaned in-memory and written to standard tables in a single pass.

#### Scenario: End-to-end daily data flow
- **WHEN** BaoStock returns raw daily bar data for a stock
- **THEN** the ETL pipeline SHALL normalize codes, convert types, and insert into `stock_daily` in one operation
- **AND** no intermediate `raw_*` table SHALL be written to
