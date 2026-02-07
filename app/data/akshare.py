import asyncio
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import akshare as ak
import pandas as pd

from app.config import settings
from app.exceptions import DataSourceError

logger = logging.getLogger(__name__)

# AKShare Chinese column name mapping
_DAILY_COLUMN_MAP = {
    "日期": "trade_date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "vol",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "pct_chg",
    "涨跌额": "change",
    "换手率": "turnover_rate",
}


def _infer_exchange(symbol: str) -> str:
    """Infer exchange suffix from 6-digit stock code prefix."""
    if symbol.startswith(("6",)):
        return "SH"
    if symbol.startswith(("0", "3")):
        return "SZ"
    if symbol.startswith(("8", "4")):
        return "BJ"
    return "SZ"


def _dec(val) -> Decimal | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


class AKShareClient:
    """AKShare data source client (backup source)."""

    def __init__(
        self,
        retry_count: int = settings.akshare_retry_count,
        retry_interval: float = settings.akshare_retry_interval,
        qps_limit: int = settings.akshare_qps_limit,
    ) -> None:
        self._retry_count = retry_count
        self._retry_interval = retry_interval
        self._semaphore = asyncio.Semaphore(qps_limit)

    async def fetch_daily(
        self, code: str, start_date: date, end_date: date
    ) -> list[dict]:
        return await self._with_retry(
            self._fetch_daily_sync, code, start_date, end_date
        )

    async def fetch_stock_list(self) -> list[dict]:
        return await self._with_retry(self._fetch_stock_list_sync)

    async def fetch_trade_calendar(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        return await self._with_retry(
            self._fetch_trade_calendar_sync, start_date, end_date
        )

    async def health_check(self) -> bool:
        try:
            df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
            return df is not None and len(df) > 0
        except Exception:
            return False

    async def _with_retry(self, sync_fn, *args):
        last_error: Exception | None = None
        for attempt in range(self._retry_count + 1):
            try:
                async with self._semaphore:
                    return await asyncio.to_thread(sync_fn, *args)
            except Exception as e:
                last_error = e
                if attempt < self._retry_count:
                    wait = self._retry_interval * (2 ** attempt)
                    logger.warning(
                        "AKShare retry %d/%d after %.1fs: %s",
                        attempt + 1, self._retry_count, wait, e,
                    )
                    await asyncio.sleep(wait)
        raise DataSourceError(
            f"AKShare failed after {self._retry_count} retries: {last_error}"
        ) from last_error

    @staticmethod
    def _fetch_daily_sync(
        code: str, start_date: date, end_date: date
    ) -> list[dict]:
        symbol = code.split(".")[0] if "." in code else code
        exchange = _infer_exchange(symbol)
        ts_code = f"{symbol}.{exchange}"

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="",
        )
        if df is None or df.empty:
            return []

        rows: list[dict] = []
        for _, row in df.iterrows():
            rows.append({
                "ts_code": ts_code,
                "trade_date": str(row.get("日期", "")),
                "open": _dec(row.get("开盘")),
                "high": _dec(row.get("最高")),
                "low": _dec(row.get("最低")),
                "close": _dec(row.get("收盘")),
                "pre_close": None,
                "vol": _dec(row.get("成交量")),
                "amount": _dec(row.get("成交额")),
                "turnover_rate": _dec(row.get("换手率")),
                "pct_chg": _dec(row.get("涨跌幅")),
                "trade_status": "1",
            })
        return rows

    @staticmethod
    def _fetch_stock_list_sync() -> list[dict]:
        df = ak.stock_info_a_code_name()
        if df is None or df.empty:
            return []

        rows: list[dict] = []
        for _, row in df.iterrows():
            symbol = str(row.get("code", ""))
            exchange = _infer_exchange(symbol)
            rows.append({
                "ts_code": f"{symbol}.{exchange}",
                "symbol": symbol,
                "name": str(row.get("name", "")),
                "industry": "",
                "area": "",
                "market": "",
                "list_date": "",
                "list_status": "L",
            })
        return rows

    @staticmethod
    def _fetch_trade_calendar_sync(
        start_date: date, end_date: date
    ) -> list[dict]:
        df = ak.tool_trade_date_hist_sina()
        if df is None or df.empty:
            return []

        trade_dates = set()
        for _, row in df.iterrows():
            d = row.get("trade_date")
            if isinstance(d, pd.Timestamp):
                d = d.date()
            if isinstance(d, date) and start_date <= d <= end_date:
                trade_dates.add(d)

        rows: list[dict] = []
        current = start_date
        while current <= end_date:
            rows.append({
                "cal_date": current.isoformat(),
                "is_open": current in trade_dates,
            })
            current = date.fromordinal(current.toordinal() + 1)
        return rows
