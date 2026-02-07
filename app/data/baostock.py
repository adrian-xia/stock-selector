import asyncio
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import baostock as bs

from app.config import settings
from app.exceptions import DataSourceError

logger = logging.getLogger(__name__)


class BaoStockClient:
    """BaoStock data source client with async wrappers over sync API."""

    def __init__(
        self,
        retry_count: int = settings.baostock_retry_count,
        retry_interval: float = settings.baostock_retry_interval,
        qps_limit: int = settings.baostock_qps_limit,
    ) -> None:
        self._retry_count = retry_count
        self._retry_interval = retry_interval
        self._semaphore = asyncio.Semaphore(qps_limit)

    # --- Public async interface ---

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
            await self._with_retry(self._health_check_sync)
            return True
        except Exception:
            return False

    # --- Retry + rate limit wrapper ---

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
                        "BaoStock retry %d/%d after %.1fs: %s",
                        attempt + 1, self._retry_count, wait, e,
                    )
                    await asyncio.sleep(wait)
        raise DataSourceError(
            f"BaoStock failed after {self._retry_count} retries: {last_error}"
        ) from last_error

    # --- Sync implementations (run in thread) ---

    @staticmethod
    def _to_standard_code(baostock_code: str) -> str:
        """Convert BaoStock code (sh.600519) to standard (600519.SH)."""
        parts = baostock_code.split(".")
        if len(parts) == 2:
            return f"{parts[1]}.{parts[0].upper()}"
        return baostock_code

    @staticmethod
    def _to_baostock_code(standard_code: str) -> str:
        """Convert standard code (600519.SH) to BaoStock (sh.600519)."""
        parts = standard_code.split(".")
        if len(parts) == 2:
            return f"{parts[1].lower()}.{parts[0]}"
        return standard_code

    def _login(self) -> None:
        result = bs.login()
        if result.error_code != "0":
            raise DataSourceError(f"BaoStock login failed: {result.error_msg}")

    def _logout(self) -> None:
        bs.logout()

    def _fetch_daily_sync(
        self, code: str, start_date: date, end_date: date
    ) -> list[dict]:
        self._login()
        try:
            bs_code = self._to_baostock_code(code)
            fields = (
                "date,code,open,high,low,close,preclose,volume,amount,"
                "turn,tradestatus,pctChg,isST"
            )
            rs = bs.query_history_k_data_plus(
                bs_code,
                fields,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                frequency="d",
                adjustflag="3",
            )
            if rs.error_code != "0":
                raise DataSourceError(
                    f"BaoStock query failed for {code}: {rs.error_msg}"
                )

            rows: list[dict] = []
            while rs.next():
                row = rs.get_row_data()
                field_names = rs.fields
                raw = dict(zip(field_names, row))
                rows.append(self._parse_daily_row(raw))
            return rows
        finally:
            self._logout()

    def _parse_daily_row(self, raw: dict) -> dict:
        def _dec(val: str) -> Decimal | None:
            if not val or val in ("", "N/A", "--", "None"):
                return None
            try:
                return Decimal(val)
            except InvalidOperation:
                return None

        return {
            "ts_code": self._to_standard_code(raw.get("code", "")),
            "trade_date": raw.get("date", ""),
            "open": _dec(raw.get("open", "")),
            "high": _dec(raw.get("high", "")),
            "low": _dec(raw.get("low", "")),
            "close": _dec(raw.get("close", "")),
            "pre_close": _dec(raw.get("preclose", "")),
            "vol": _dec(raw.get("volume", "")),
            "amount": _dec(raw.get("amount", "")),
            "turnover_rate": _dec(raw.get("turn", "")),
            "pct_chg": _dec(raw.get("pctChg", "")),
            "trade_status": "1" if raw.get("tradestatus") == "1" else "0",
        }

    def _fetch_stock_list_sync(self) -> list[dict]:
        self._login()
        try:
            rs = bs.query_stock_basic()
            if rs.error_code != "0":
                raise DataSourceError(
                    f"BaoStock stock list query failed: {rs.error_msg}"
                )
            rows: list[dict] = []
            while rs.next():
                row = rs.get_row_data()
                field_names = rs.fields
                raw = dict(zip(field_names, row))
                ts_code = self._to_standard_code(raw.get("code", ""))
                rows.append({
                    "ts_code": ts_code,
                    "symbol": ts_code.split(".")[0] if "." in ts_code else ts_code,
                    "name": raw.get("code_name", ""),
                    "industry": "",
                    "area": "",
                    "market": "",
                    "list_date": raw.get("ipoDate", ""),
                    "list_status": "D" if raw.get("outDate", "") else "L",
                })
            return rows
        finally:
            self._logout()

    def _fetch_trade_calendar_sync(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        self._login()
        try:
            rs = bs.query_trade_dates(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            if rs.error_code != "0":
                raise DataSourceError(
                    f"BaoStock trade calendar query failed: {rs.error_msg}"
                )
            rows: list[dict] = []
            while rs.next():
                row = rs.get_row_data()
                field_names = rs.fields
                raw = dict(zip(field_names, row))
                rows.append({
                    "cal_date": raw.get("calendar_date", ""),
                    "is_open": raw.get("is_trading_day", "0") == "1",
                })
            return rows
        finally:
            self._logout()

    def _health_check_sync(self) -> bool:
        self._login()
        self._logout()
        return True
