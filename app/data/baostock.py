import asyncio
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

import baostock as bs

from app.config import settings
from app.exceptions import DataSourceError

if TYPE_CHECKING:
    from app.data.pool import BaoStockConnectionPool

logger = logging.getLogger(__name__)


class BaoStockClient:
    """BaoStock data source client with async wrappers over sync API.

    支持可选的连接池参数，用于复用 BaoStock 登录会话。
    如果不提供连接池，则使用旧逻辑（每次请求 login/logout）。
    """

    def __init__(
        self,
        retry_count: int = settings.baostock_retry_count,
        retry_interval: float = settings.baostock_retry_interval,
        qps_limit: int = settings.baostock_qps_limit,
        connection_pool: "BaoStockConnectionPool | None" = None,
    ) -> None:
        self._retry_count = retry_count
        self._retry_interval = retry_interval
        self._semaphore = asyncio.Semaphore(qps_limit)
        self._pool = connection_pool

    # --- Public async interface ---

    async def fetch_daily(
        self, code: str, start_date: date, end_date: date
    ) -> list[dict]:
        if self._pool:
            session = await self._pool.acquire()
            try:
                return await self._with_retry(
                    self._fetch_daily_sync, code, start_date, end_date, session
                )
            finally:
                await self._pool.release(session)
        else:
            return await self._with_retry(
                self._fetch_daily_sync, code, start_date, end_date, None
            )

    async def fetch_stock_list(self) -> list[dict]:
        if self._pool:
            session = await self._pool.acquire()
            try:
                return await self._with_retry(self._fetch_stock_list_sync, session)
            finally:
                await self._pool.release(session)
        else:
            return await self._with_retry(self._fetch_stock_list_sync, None)

    async def fetch_trade_calendar(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        if self._pool:
            session = await self._pool.acquire()
            try:
                return await self._with_retry(
                    self._fetch_trade_calendar_sync, start_date, end_date, session
                )
            finally:
                await self._pool.release(session)
        else:
            return await self._with_retry(
                self._fetch_trade_calendar_sync, start_date, end_date, None
            )

    async def health_check(self) -> bool:
        try:
            await self._with_retry(self._health_check_sync)
            return True
        except Exception:
            return False

    async def fetch_adj_factor(
        self, code: str, start_date: date, end_date: date
    ) -> list[dict]:
        """获取复权因子数据。

        调用 BaoStock query_adjust_factor() 接口，返回前复权因子。

        Args:
            code: 标准股票代码，如 "600519.SH"
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            list[dict]，每个 dict 含 ts_code, trade_date, adj_factor
        """
        if self._pool:
            session = await self._pool.acquire()
            try:
                return await self._with_retry(
                    self._fetch_adj_factor_sync, code, start_date, end_date, session
                )
            finally:
                await self._pool.release(session)
        else:
            return await self._with_retry(
                self._fetch_adj_factor_sync, code, start_date, end_date, None
            )

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
        self, code: str, start_date: date, end_date: date, session=None
    ) -> list[dict]:
        """同步获取日线数据。

        如果提供了 session，直接使用；否则使用旧逻辑 login/logout。
        """
        if session is not None:
            # 使用连接池会话（已在异步层面获取）
            return self._query_daily(code, start_date, end_date)
        else:
            # 旧逻辑：login → query → logout
            self._login()
            try:
                return self._query_daily(code, start_date, end_date)
            finally:
                self._logout()

    def _query_daily(
        self, code: str, start_date: date, end_date: date
    ) -> list[dict]:
        """执行日线数据查询（假设已登录）。"""
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

    def _fetch_stock_list_sync(self, session=None) -> list[dict]:
        """同步获取股票列表。"""
        if session is not None:
            return self._query_stock_list()
        else:
            self._login()
            try:
                return self._query_stock_list()
            finally:
                self._logout()

    def _query_stock_list(self) -> list[dict]:
        """执行股票列表查询（假设已登录）。"""
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

    def _fetch_trade_calendar_sync(
        self, start_date: date, end_date: date, session=None
    ) -> list[dict]:
        """同步获取交易日历。"""
        if session is not None:
            return self._query_trade_calendar(start_date, end_date)
        else:
            self._login()
            try:
                return self._query_trade_calendar(start_date, end_date)
            finally:
                self._logout()

    def _query_trade_calendar(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """执行交易日历查询（假设已登录）。"""
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

    def _health_check_sync(self) -> bool:
        self._login()
        self._logout()
        return True

    def _fetch_adj_factor_sync(
        self, code: str, start_date: date, end_date: date, session=None
    ) -> list[dict]:
        """同步获取复权因子。"""
        if session is not None:
            return self._query_adj_factor(code, start_date, end_date)
        else:
            self._login()
            try:
                return self._query_adj_factor(code, start_date, end_date)
            finally:
                self._logout()

    def _query_adj_factor(
        self, code: str, start_date: date, end_date: date
    ) -> list[dict]:
        """执行复权因子查询（假设已登录）。"""
        bs_code = self._to_baostock_code(code)
        rs = bs.query_adjust_factor(
            code=bs_code,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        if rs.error_code != "0":
            raise DataSourceError(
                f"BaoStock adj_factor query failed for {code}: {rs.error_msg}"
            )

        rows: list[dict] = []
        while rs.next():
            row = rs.get_row_data()
            field_names = rs.fields
            raw = dict(zip(field_names, row))
            adj_val = raw.get("foreAdjustFactor", "")
            if not adj_val or adj_val in ("", "N/A", "--", "None"):
                continue
            try:
                adj_factor = Decimal(adj_val)
            except InvalidOperation:
                continue
            rows.append({
                "ts_code": self._to_standard_code(raw.get("code", bs_code)),
                "trade_date": raw.get("dividOperateDate", ""),
                "adj_factor": adj_factor,
            })
        return rows
