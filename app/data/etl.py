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
    """Normalize stock codes to standard format (600519.SH)."""
    if not raw_code:
        return raw_code

    # Tushare 原生格式已经是 600519.SH，直接透传
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


# =====================================================================
# P3 指数数据 ETL 清洗函数（6 个）
# =====================================================================


def transform_tushare_index_basic(raw_rows: list[dict]) -> list[dict]:
    """清洗指数基础信息（raw_tushare_index_basic → index_basic）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "ts_code": raw["ts_code"],
            "name": raw.get("name"),
            "fullname": raw.get("fullname"),
            "market": raw.get("market"),
            "publisher": raw.get("publisher"),
            "index_type": raw.get("index_type"),
            "category": raw.get("category"),
            "base_date": parse_date(raw.get("base_date")),
            "base_point": parse_decimal(raw.get("base_point")),
            "list_date": parse_date(raw.get("list_date")),
            "weight_rule": raw.get("weight_rule"),
            "desc": raw.get("desc"),
            "exp_date": parse_date(raw.get("exp_date")),
        })
    return cleaned


def transform_tushare_index_daily(raw_rows: list[dict]) -> list[dict]:
    """清洗指数日线行情（raw_tushare_index_daily → index_daily）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "ts_code": raw["ts_code"],
            "trade_date": parse_date(raw["trade_date"]),
            "open": parse_decimal(raw.get("open")),
            "high": parse_decimal(raw.get("high")),
            "low": parse_decimal(raw.get("low")),
            "close": parse_decimal(raw.get("close")),
            "pre_close": parse_decimal(raw.get("pre_close")),
            "change": parse_decimal(raw.get("change")),
            "pct_chg": parse_decimal(raw.get("pct_chg")),
            "vol": parse_decimal(raw.get("vol")) or Decimal("0"),
            "amount": parse_decimal(raw.get("amount")) or Decimal("0"),
        })
    return cleaned


def transform_tushare_index_weight(raw_rows: list[dict]) -> list[dict]:
    """清洗指数成分股权重（raw_tushare_index_weight → index_weight）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "index_code": raw["index_code"],
            "con_code": raw["con_code"],
            "trade_date": parse_date(raw["trade_date"]),
            "weight": parse_decimal(raw.get("weight")),
        })
    return cleaned


def transform_tushare_industry_classify(raw_rows: list[dict]) -> list[dict]:
    """清洗行业分类（raw_tushare_index_classify → industry_classify）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "index_code": raw["index_code"],
            "industry_name": raw.get("industry_name"),
            "level": raw.get("level"),
            "industry_code": raw.get("industry_code"),
            "src": raw.get("src"),
        })
    return cleaned


def transform_tushare_industry_member(raw_rows: list[dict]) -> list[dict]:
    """清洗行业成分股（raw_tushare_index_member_all → industry_member）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "index_code": raw["index_code"],
            "con_code": raw["con_code"],
            "in_date": parse_date(raw["in_date"]),
            "out_date": parse_date(raw.get("out_date")),
            "is_new": raw.get("is_new"),
        })
    return cleaned


def transform_tushare_index_technical(raw_rows: list[dict]) -> list[dict]:
    """清洗指数技术指标（raw_tushare_index_factor_pro → index_technical_daily）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "ts_code": raw["ts_code"],
            "trade_date": parse_date(raw["trade_date"]),
            # 均线指标
            "ma5": parse_decimal(raw.get("ma5")),
            "ma10": parse_decimal(raw.get("ma10")),
            "ma20": parse_decimal(raw.get("ma20")),
            "ma60": parse_decimal(raw.get("ma60")),
            "ma120": parse_decimal(raw.get("ma120")),
            "ma250": parse_decimal(raw.get("ma250")),
            # MACD 指标
            "macd_dif": parse_decimal(raw.get("macd_dif")),
            "macd_dea": parse_decimal(raw.get("macd_dea")),
            "macd_hist": parse_decimal(raw.get("macd")),  # raw 表中是 macd，业务表中是 macd_hist
            # KDJ 指标
            "kdj_k": parse_decimal(raw.get("kdj_k")),
            "kdj_d": parse_decimal(raw.get("kdj_d")),
            "kdj_j": parse_decimal(raw.get("kdj_j")),
            # RSI 指标
            "rsi6": parse_decimal(raw.get("rsi6")),
            "rsi12": parse_decimal(raw.get("rsi12")),
            "rsi24": parse_decimal(raw.get("rsi24")),
            # 布林带指标
            "boll_upper": parse_decimal(raw.get("boll_upper")),
            "boll_mid": parse_decimal(raw.get("boll_mid")),
            "boll_lower": parse_decimal(raw.get("boll_lower")),
            # 成交量指标（raw 表中没有，需要自己计算）
            "vol_ma5": None,
            "vol_ma10": None,
            "vol_ratio": None,
            # 其他指标
            "atr14": parse_decimal(raw.get("atr")),
            "cci14": parse_decimal(raw.get("cci")),
            "willr14": parse_decimal(raw.get("wr")),
        })
    return cleaned


# =====================================================================
# P4 板块数据 ETL 清洗函数（3 个）
# =====================================================================


def transform_tushare_concept_index(raw_rows: list[dict], src: str) -> list[dict]:
    """清洗板块基础信息（raw_tushare_ths_index/dc_index/tdx_index → concept_index）。

    统一三个数据源（THS/DC/TDX）到 concept_index 业务表。

    Args:
        raw_rows: 原始数据行列表
        src: 数据源标识（THS/DC/TDX）

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "ts_code": raw["ts_code"],
            "name": raw.get("name"),
            "src": src,
            "type": raw.get("type"),
        })
    return cleaned


def transform_tushare_concept_daily(raw_rows: list[dict]) -> list[dict]:
    """清洗板块日线行情（raw_tushare_ths_daily → concept_daily）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "ts_code": raw["ts_code"],
            "trade_date": parse_date(raw["trade_date"]),
            "open": parse_decimal(raw.get("open")),
            "high": parse_decimal(raw.get("high")),
            "low": parse_decimal(raw.get("low")),
            "close": parse_decimal(raw.get("close")),
            "pre_close": parse_decimal(raw.get("pre_close")),
            "change": parse_decimal(raw.get("change")),
            "pct_chg": parse_decimal(raw.get("pct_chg")),
            "vol": parse_decimal(raw.get("vol")) or Decimal("0"),
            "amount": parse_decimal(raw.get("amount")) or Decimal("0"),
        })
    return cleaned


def transform_tushare_concept_member(raw_rows: list[dict]) -> list[dict]:
    """清洗板块成分股（raw_tushare_ths_member/dc_member/tdx_member → concept_member）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    cleaned = []
    for raw in raw_rows:
        cleaned.append({
            "concept_code": raw["ts_code"],
            "stock_code": raw["code"],
            "in_date": parse_date(raw["in_date"]),
            "out_date": parse_date(raw.get("out_date")),
        })
    return cleaned


# ---------------------------------------------------------------------------
# P2 资金流向 ETL
# ---------------------------------------------------------------------------


def transform_tushare_moneyflow(raw_rows: list[dict]) -> list[dict]:
    """将 Tushare moneyflow 原始数据转换为 money_flow 业务表格式。

    字段一一对应，日期 VARCHAR(8) → DATE，数值 NUMERIC → Decimal，NaN/None → 0。
    """
    if not raw_rows:
        return []

    _ZERO = Decimal("0")
    cleaned: list[dict] = []
    for raw in raw_rows:
        ts_code = raw.get("ts_code", "")
        if not ts_code:
            continue
        trade_date = parse_date(raw.get("trade_date"))
        if trade_date is None:
            continue

        cleaned.append({
            "ts_code": ts_code,
            "trade_date": trade_date,
            "buy_sm_vol": parse_decimal(raw.get("buy_sm_vol")) or _ZERO,
            "buy_sm_amount": parse_decimal(raw.get("buy_sm_amount")) or _ZERO,
            "sell_sm_vol": parse_decimal(raw.get("sell_sm_vol")) or _ZERO,
            "sell_sm_amount": parse_decimal(raw.get("sell_sm_amount")) or _ZERO,
            "buy_md_vol": parse_decimal(raw.get("buy_md_vol")) or _ZERO,
            "buy_md_amount": parse_decimal(raw.get("buy_md_amount")) or _ZERO,
            "sell_md_vol": parse_decimal(raw.get("sell_md_vol")) or _ZERO,
            "sell_md_amount": parse_decimal(raw.get("sell_md_amount")) or _ZERO,
            "buy_lg_vol": parse_decimal(raw.get("buy_lg_vol")) or _ZERO,
            "buy_lg_amount": parse_decimal(raw.get("buy_lg_amount")) or _ZERO,
            "sell_lg_vol": parse_decimal(raw.get("sell_lg_vol")) or _ZERO,
            "sell_lg_amount": parse_decimal(raw.get("sell_lg_amount")) or _ZERO,
            "buy_elg_vol": parse_decimal(raw.get("buy_elg_vol")) or _ZERO,
            "buy_elg_amount": parse_decimal(raw.get("buy_elg_amount")) or _ZERO,
            "sell_elg_vol": parse_decimal(raw.get("sell_elg_vol")) or _ZERO,
            "sell_elg_amount": parse_decimal(raw.get("sell_elg_amount")) or _ZERO,
            "net_mf_amount": parse_decimal(raw.get("net_mf_amount")) or _ZERO,
            "data_source": "tushare",
        })
    return cleaned


def transform_tushare_top_list(raw_rows: list[dict]) -> list[dict]:
    """将 Tushare top_list 原始数据转换为 dragon_tiger 业务表格式。

    字段映射：l_buy → buy_total, l_sell → sell_total, net_amount → net_buy。
    """
    if not raw_rows:
        return []

    cleaned: list[dict] = []
    for raw in raw_rows:
        ts_code = raw.get("ts_code", "")
        if not ts_code:
            continue
        trade_date = parse_date(raw.get("trade_date"))
        if trade_date is None:
            continue

        cleaned.append({
            "ts_code": ts_code,
            "trade_date": trade_date,
            "reason": _safe_str(raw.get("reason")) or None,
            "buy_total": parse_decimal(raw.get("l_buy")),
            "sell_total": parse_decimal(raw.get("l_sell")),
            "net_buy": parse_decimal(raw.get("net_amount")),
            "list_name": _safe_str(raw.get("name")) or None,
            "data_source": "tushare",
        })
    return cleaned


def transform_tushare_top_inst(raw_rows: list[dict]) -> list[dict]:
    """将 Tushare top_inst 原始数据转换为标准格式（备用）。"""
    if not raw_rows:
        return []

    cleaned: list[dict] = []
    for raw in raw_rows:
        ts_code = raw.get("ts_code", "")
        if not ts_code:
            continue
        trade_date = parse_date(raw.get("trade_date"))
        if trade_date is None:
            continue

        cleaned.append({
            "ts_code": ts_code,
            "trade_date": trade_date,
            "exalter": _safe_str(raw.get("exalter")),
            "side": _safe_str(raw.get("side")) or None,
            "buy": parse_decimal(raw.get("buy")),
            "buy_rate": parse_decimal(raw.get("buy_rate")),
            "sell": parse_decimal(raw.get("sell")),
            "sell_rate": parse_decimal(raw.get("sell_rate")),
            "net_buy": parse_decimal(raw.get("net_buy")),
            "reason": _safe_str(raw.get("reason")) or None,
        })
    return cleaned


# ---------------------------------------------------------------------------
# P5 扩展数据 ETL
# ---------------------------------------------------------------------------


def transform_tushare_suspend_d(raw_rows: list[dict]) -> list[dict]:
    """清洗停复牌数据（raw_tushare_suspend_d → suspend_info）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    if not raw_rows:
        return []

    cleaned: list[dict] = []
    for raw in raw_rows:
        ts_code = raw.get("ts_code", "")
        if not ts_code:
            continue
        trade_date = parse_date(raw.get("suspend_date"))
        if trade_date is None:
            continue

        cleaned.append({
            "ts_code": ts_code,
            "trade_date": trade_date,
            "suspend_timing": _safe_str(raw.get("suspend_timing")) or None,
            "suspend_type": _safe_str(raw.get("reason_type")) or None,
            "suspend_reason": _safe_str(raw.get("suspend_reason")) or None,
            "resume_date": parse_date(raw.get("resume_date")),
            "data_source": "tushare",
        })
    return cleaned


def transform_tushare_limit_list_d(raw_rows: list[dict]) -> list[dict]:
    """清洗涨跌停统计数据（raw_tushare_limit_list_d → limit_list_daily）。

    Args:
        raw_rows: 原始数据行列表

    Returns:
        清洗后的数据行列表
    """
    if not raw_rows:
        return []

    cleaned: list[dict] = []
    for raw in raw_rows:
        ts_code = raw.get("ts_code", "")
        if not ts_code:
            continue
        trade_date = parse_date(raw.get("trade_date"))
        if trade_date is None:
            continue

        cleaned.append({
            "ts_code": ts_code,
            "trade_date": trade_date,
            "name": _safe_str(raw.get("name")) or None,
            "close": parse_decimal(raw.get("close")),
            "pct_chg": parse_decimal(raw.get("pct_chg")),
            "amp": parse_decimal(raw.get("amp")),
            "fc_ratio": parse_decimal(raw.get("fc_ratio")),
            "fl_ratio": parse_decimal(raw.get("fl_ratio")),
            "fd_amount": parse_decimal(raw.get("fd_amount")),
            "first_time": _safe_str(raw.get("first_time")) or None,
            "last_time": _safe_str(raw.get("last_time")) or None,
            "open_times": int(raw["open_times"]) if raw.get("open_times") is not None else None,
            "up_stat": _safe_str(raw.get("up_stat")) or None,
            "limit_times": int(raw["limit_times"]) if raw.get("limit_times") is not None else None,
            "data_source": "tushare",
        })
    return cleaned

