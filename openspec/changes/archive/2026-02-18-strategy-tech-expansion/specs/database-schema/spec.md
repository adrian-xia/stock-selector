## MODIFIED Requirements

### Requirement: technical_daily table schema
The `technical_daily` table SHALL contain the following additional columns beyond the existing 23 indicator columns:

- `wr`: Numeric(10,4), nullable — Williams %R (14-period)
- `cci`: Numeric(10,4), nullable — CCI (14-period)
- `bias`: Numeric(10,4), nullable — BIAS based on MA20
- `obv`: Numeric(20,2), nullable — On-Balance Volume (cumulative)
- `donchian_upper`: Numeric(10,2), nullable — Donchian channel upper band (20-period)
- `donchian_lower`: Numeric(10,2), nullable — Donchian channel lower band (20-period)

All new columns SHALL be nullable with default NULL to maintain backward compatibility.

#### Scenario: New columns exist after migration
- **WHEN** `alembic upgrade head` is executed
- **THEN** the `technical_daily` table SHALL have columns `wr`, `cci`, `bias`, `obv`, `donchian_upper`, `donchian_lower`

#### Scenario: Existing data unaffected
- **WHEN** migration runs on a table with existing data
- **THEN** all existing rows SHALL have NULL values for the 6 new columns
