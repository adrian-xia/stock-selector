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


def _safe_str(val, default: str = "") -> str:
    """将值安全转换为字符串，NaN/None 返回默认值。"""
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    return str(val)


def normalize_stock_code(raw_code: str, source: str = "tushare") -> str:
    """Normalize stock codes from various sources to standard format (600519.SH)."""
    if not raw_code:
        return raw_code

    if source == "tushare":
        # Tushare 原生格式已经是 600519.SH，直接透传
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


def transform_tushare_stock_basic(raw_rows: list[dict]) -> list[dict]:
    """将 Tushare stock_basic 原始数据转换为 stocks 业务表格式。"""
    cleaned: list[dict] = []
    for raw in raw_rows:
        ts_code = raw.get("ts_code", "")
        if not ts_code:
            continue
        cleaned.append({
            "ts_code": ts_code,
            "symbol": _safe_str(raw.get("symbol", ts_code.split(".")[0])),
            "name": _safe_str(raw.get("name", "")),
            "area": _safe_str(raw.get("area", "")),
            "industry": _safe_str(raw.get("industry", "")),
            "market": _safe_str(raw.get("market", "")),
            "list_date": parse_date(raw.get("list_date")),
            "delist_date": parse_date(raw.get("delist_date")),
            "list_status": _safe_str(raw.get("list_status", "L")),
        })
    return cleaned


def transform_tushare_trade_cal(raw_rows: list[dict]) -> list[dict]:
    """将 Tushare trade_cal 原始数据转换为 trade_calendar 业务表格式。"""
    cleaned: list[dict] = []
    for raw in raw_rows:
        cal_date = parse_date(raw.get("cal_date"))
        if cal_date is None:
            continue
        is_open = raw.get("is_open", 0)
        pre_trade_date = parse_date(raw.get("pretrade_date"))
        cleaned.append({
            "cal_date": cal_date,
            "exchange": raw.get("exchange", "SSE"),
            "is_open": int(is_open) == 1 if not isinstance(is_open, bool) else is_open,
            "pre_trade_date": pre_trade_date,
        })
    return cleaned


def transform_tushare_daily(
    raw_daily: list[dict],
    raw_adj_factor: list[dict],
    raw_daily_basic: list[dict],
) -> list[dict]:
    """将 Tushare daily + adj_factor + daily_basic 原始数据合并转换为 stock_daily 业务表格式。

    注意：Tushare daily 的 amount 单位是千元，需要乘以 1000 转换为元。
    """
    # 构建 adj_factor 和 daily_basic 的查找表
    adj_map: dict[str, Decimal | None] = {}
    for r in raw_adj_factor:
        key = f"{r.get('ts_code')}_{r.get('trade_date')}"
        adj_map[key] = parse_decimal(r.get("adj_factor"))

    basic_map: dict[str, Decimal | None] = {}
    for r in raw_daily_basic:
        key = f"{r.get('ts_code')}_{r.get('trade_date')}"
        basic_map[key] = parse_decimal(r.get("turnover_rate"))

    cleaned: list[dict] = []
    for raw in raw_daily:
        trade_date = parse_date(raw.get("trade_date"))
        if trade_date is None:
            continue

        ts_code = raw.get("ts_code", "")
        key = f"{ts_code}_{raw.get('trade_date')}"

        vol = parse_decimal(raw.get("vol"))
        # amount 千元 → 元
        amount_raw = parse_decimal(raw.get("amount"))
        amount = amount_raw * 1000 if amount_raw is not None else Decimal("0")

        trade_status = "1"
        if vol is not None and vol == 0 and amount == 0:
            trade_status = "0"

        cleaned.append({
            "ts_code": ts_code,
            "trade_date": trade_date,
            "open": parse_decimal(raw.get("open")),
            "high": parse_decimal(raw.get("high")),
            "low": parse_decimal(raw.get("low")),
            "close": parse_decimal(raw.get("close")),
            "pre_close": parse_decimal(raw.get("pre_close")),
            "pct_chg": parse_decimal(raw.get("pct_chg")),
            "vol": vol or Decimal("0"),
            "amount": amount,
            "adj_factor": adj_map.get(key),
            "turnover_rate": basic_map.get(key),
            "trade_status": trade_status,
            "data_source": "tushare",
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


def transform_tushare_fina_indicator(raw_rows: list[dict]) -> list[dict]:
    """将 Tushare fina_indicator 原始数据转换为 finance_indicator 业务表格式。

    从 raw_tushare_fina_indicator 的 100+ 字段中提取核心财务指标。

    Args:
        raw_rows: raw_tushare_fina_indicator 表的原始数据

    Returns:
        finance_indicator 表格式的清洗数据
    """
    cleaned: list[dict] = []
    for raw in raw_rows:
        ts_code = raw.get("ts_code", "")
        if not ts_code:
            continue

        end_date = parse_date(raw.get("end_date"))
        ann_date = parse_date(raw.get("ann_date"))
        if end_date is None or ann_date is None:
            continue

        # 从 raw 表的 100+ 字段中提取核心指标
        cleaned.append({
            "ts_code": ts_code,
            "end_date": end_date,
            "ann_date": ann_date,
            "report_type": _safe_str(raw.get("update_flag", "")),  # 更新标志作为报告类型
            # 每股指标
            "eps": parse_decimal(raw.get("eps")),
            "ocf_per_share": parse_decimal(raw.get("ocfps")),
            # 盈利能力
            "roe": parse_decimal(raw.get("roe")),
            "roe_diluted": parse_decimal(raw.get("roe_dt")),
            "gross_margin": parse_decimal(raw.get("grossprofit_margin")),
            "net_margin": parse_decimal(raw.get("netprofit_margin")),
            # 同比增长率
            "revenue_yoy": parse_decimal(raw.get("or_yoy")),
            "profit_yoy": parse_decimal(raw.get("netprofit_yoy")),
            # 估值指标（从 raw_tushare_daily_basic 获取，这里暂时为 None）
            "pe_ttm": None,
            "pb": None,
            "ps_ttm": None,
            "total_mv": None,
            "circ_mv": None,
            # 偿债能力
            "current_ratio": parse_decimal(raw.get("current_ratio")),
            "quick_ratio": parse_decimal(raw.get("quick_ratio")),
            "debt_ratio": parse_decimal(raw.get("debt_to_assets")),
            # 数据源
            "data_source": "tushare",
        })
    return cleaned

