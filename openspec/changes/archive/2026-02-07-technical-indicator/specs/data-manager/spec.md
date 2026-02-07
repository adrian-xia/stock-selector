## ADDED Requirements

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
