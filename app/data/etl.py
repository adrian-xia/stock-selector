import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

_NULL_VALUES = {"", "N/A", "--", "None", "none", "null", "NULL"}


def normalize_stock_code(raw_code: str, source: str = "baostock") -> str:
    """Normalize stock codes from various sources to standard format (600519.SH)."""
    if not raw_code:
        return raw_code

    if source == "baostock":
        # sh.600519 -> 600519.SH
        parts = raw_code.split(".")
        if len(parts) == 2 and parts[0] in ("sh", "sz", "bj"):
            return f"{parts[1]}.{parts[0].upper()}"
        return raw_code

    if source == "akshare":
        # 600519 -> 600519.SH
        symbol = raw_code.strip()
        if symbol.startswith(("6",)):
            return f"{symbol}.SH"
        if symbol.startswith(("0", "3")):
            return f"{symbol}.SZ"
        if symbol.startswith(("8", "4")):
            return f"{symbol}.BJ"
        return f"{symbol}.SZ"

    return raw_code


def parse_decimal(value: str | float | None) -> Decimal | None:
    """Parse a string or float value into Decimal, returning None for empty/invalid."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    s = str(value).strip()
    if s in _NULL_VALUES:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: str | None) -> date | None:
    """Parse date string in YYYY-MM-DD or YYYYMMDD format."""
    if not value or str(value).strip() in _NULL_VALUES:
        return None
    s = str(value).strip()
    try:
        if "-" in s:
            return datetime.strptime(s, "%Y-%m-%d").date()
        if len(s) == 8:
            return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        pass
    return None


def clean_baostock_daily(raw_rows: list[dict]) -> list[dict]:
    """Clean BaoStock daily bar data into standard format."""
    cleaned: list[dict] = []
    for raw in raw_rows:
        trade_date = parse_date(raw.get("trade_date"))
        if trade_date is None:
            continue

        vol = parse_decimal(raw.get("vol"))
        amount = parse_decimal(raw.get("amount"))
        trade_status = raw.get("trade_status", "1")
        if vol is not None and vol == 0 and amount is not None and amount == 0:
            trade_status = "0"

        cleaned.append({
            "ts_code": raw.get("ts_code", ""),
            "trade_date": trade_date,
            "open": parse_decimal(raw.get("open")),
            "high": parse_decimal(raw.get("high")),
            "low": parse_decimal(raw.get("low")),
            "close": parse_decimal(raw.get("close")),
            "pre_close": parse_decimal(raw.get("pre_close")),
            "pct_chg": parse_decimal(raw.get("pct_chg")),
            "vol": vol or Decimal("0"),
            "amount": amount or Decimal("0"),
            "turnover_rate": parse_decimal(raw.get("turnover_rate")),
            "trade_status": trade_status,
            "data_source": "baostock",
        })
    return cleaned


def clean_akshare_daily(raw_rows: list[dict]) -> list[dict]:
    """Clean AKShare daily bar data into standard format."""
    cleaned: list[dict] = []
    for raw in raw_rows:
        trade_date = parse_date(raw.get("trade_date"))
        if trade_date is None:
            continue

        vol = parse_decimal(raw.get("vol"))
        amount = parse_decimal(raw.get("amount"))

        cleaned.append({
            "ts_code": raw.get("ts_code", ""),
            "trade_date": trade_date,
            "open": parse_decimal(raw.get("open")),
            "high": parse_decimal(raw.get("high")),
            "low": parse_decimal(raw.get("low")),
            "close": parse_decimal(raw.get("close")),
            "pre_close": parse_decimal(raw.get("pre_close")),
            "pct_chg": parse_decimal(raw.get("pct_chg")),
            "vol": vol or Decimal("0"),
            "amount": amount or Decimal("0"),
            "turnover_rate": parse_decimal(raw.get("turnover_rate")),
            "trade_status": raw.get("trade_status", "1"),
            "data_source": "akshare",
        })
    return cleaned


def clean_baostock_stock_list(raw_rows: list[dict]) -> list[dict]:
    """Clean BaoStock stock list data."""
    cleaned: list[dict] = []
    for raw in raw_rows:
        ts_code = raw.get("ts_code", "")
        if not ts_code:
            continue
        list_date = parse_date(raw.get("list_date"))
        cleaned.append({
            "ts_code": ts_code,
            "symbol": raw.get("symbol", ts_code.split(".")[0]),
            "name": raw.get("name", ""),
            "area": raw.get("area", ""),
            "industry": raw.get("industry", ""),
            "market": raw.get("market", ""),
            "list_date": list_date,
            "list_status": raw.get("list_status", "L"),
        })
    return cleaned


def clean_baostock_trade_calendar(raw_rows: list[dict]) -> list[dict]:
    """Clean BaoStock trade calendar data."""
    cleaned: list[dict] = []
    for raw in raw_rows:
        cal_date = parse_date(raw.get("cal_date"))
        if cal_date is None:
            continue
        cleaned.append({
            "cal_date": cal_date,
            "exchange": "SSE",
            "is_open": bool(raw.get("is_open", False)),
        })
    return cleaned


async def batch_insert(
    session: AsyncSession,
    table: Table,
    rows: list[dict],
    batch_size: int = settings.etl_batch_size,
) -> int:
    """Batch insert rows using INSERT ... ON CONFLICT DO NOTHING.

    自动根据列数调整 batch_size，确保不超过 asyncpg 32767 参数限制。

    Returns the total number of rows processed.
    """
    if not rows:
        return 0

    # asyncpg 参数上限 32767，根据列数动态调整 batch_size
    num_columns = len(rows[0])
    max_batch = 32000 // num_columns  # 留一点余量
    batch_size = min(batch_size, max_batch)

    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        stmt = pg_insert(table).values(batch).on_conflict_do_nothing()
        await session.execute(stmt)
        total += len(batch)

    await session.commit()
    return total
