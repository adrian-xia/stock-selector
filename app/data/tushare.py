"""Tushare Pro API 客户端。

令牌桶限流 + asyncio.to_thread 异步包装 + 自动重试。
实现 DataSourceClient Protocol，同时提供 fetch_raw_* 系列方法获取原始数据。
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

import tushare as ts

from app.config import settings
from app.exceptions import DataSourceError

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class _TokenBucket:
    """令牌桶限流器。

    以固定速率补充令牌，每次 API 调用消耗一个令牌。
    当令牌不足时异步等待，确保不超过 Tushare 频率限制。
    """

    def __init__(self, rate_per_minute: int) -> None:
        self._rate = rate_per_minute / 60.0  # 每秒补充令牌数
        self._max_tokens = float(rate_per_minute)
        self._tokens = float(rate_per_minute)  # 初始满桶
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """获取一个令牌，令牌不足时等待。"""
        async with self._lock:
            self._refill()
            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait_time)
                self._refill()
            self._tokens -= 1.0

    def _refill(self) -> None:
        """根据经过的时间补充令牌。"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._rate)
        self._last_refill = now


class TushareClient:
    """Tushare Pro API 客户端。

    - 令牌桶限流（默认 400 次/分钟，官方限制 500）
    - asyncio.to_thread 异步包装（Tushare SDK 是同步的）
    - 指数退避重试
    - 实现 DataSourceClient Protocol 的 4 个方法
    - 提供 fetch_raw_* 系列方法获取原始数据
    """

    def __init__(
        self,
        token: str = settings.tushare_token,
        retry_count: int = settings.tushare_retry_count,
        retry_interval: float = settings.tushare_retry_interval,
        qps_limit: int = settings.tushare_qps_limit,
    ) -> None:
        self._token = token
        self._retry_count = retry_count
        self._retry_interval = retry_interval
        self._bucket = _TokenBucket(qps_limit)
        # 初始化 Tushare Pro API（同步）
        self._pro = ts.pro_api(token)

    # ------------------------------------------------------------------
    # DataSourceClient Protocol 方法
    # ------------------------------------------------------------------

    async def fetch_stock_list(self) -> list[dict]:
        """获取全部 A 股列表（含退市）。"""
        rows: list[dict] = []
        for status in ("L", "D", "P"):
            df = await self._call(
                "stock_basic",
                exchange="",
                list_status=status,
                fields="ts_code,symbol,name,area,industry,market,list_date,delist_date,list_status",
            )
            for _, row in df.iterrows():
                rows.append({
                    "ts_code": row["ts_code"],
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "area": row.get("area", ""),
                    "industry": row.get("industry", ""),
                    "market": row.get("market", ""),
                    "list_date": row.get("list_date", ""),
                    "delist_date": row.get("delist_date") or None,
                    "list_status": row.get("list_status", "L"),
                })
        return rows

    async def fetch_trade_calendar(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """获取交易日历。"""
        df = await self._call(
            "trade_cal",
            exchange="SSE",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
        rows: list[dict] = []
        for _, row in df.iterrows():
            rows.append({
                "cal_date": row["cal_date"],
                "is_open": int(row["is_open"]) == 1,
                "pretrade_date": row.get("pretrade_date", ""),
            })
        return rows

    async def fetch_daily(
        self, code: str, start_date: date, end_date: date
    ) -> list[dict]:
        """获取单只股票日线数据（Protocol 兼容方法）。

        内部调用 daily + adj_factor + daily_basic 三个接口，
        合并后返回与 BaoStockClient 兼容的格式。
        """
        sd = start_date.strftime("%Y%m%d")
        ed = end_date.strftime("%Y%m%d")

        df_daily = await self._call("daily", ts_code=code, start_date=sd, end_date=ed)
        df_adj = await self._call("adj_factor", ts_code=code, start_date=sd, end_date=ed)
        df_basic = await self._call(
            "daily_basic", ts_code=code, start_date=sd, end_date=ed,
            fields="ts_code,trade_date,turnover_rate",
        )

        # 以 trade_date 为 key 合并
        adj_map = {r["trade_date"]: r.get("adj_factor") for _, r in df_adj.iterrows()}
        basic_map = {r["trade_date"]: r.get("turnover_rate") for _, r in df_basic.iterrows()}

        rows: list[dict] = []
        for _, r in df_daily.iterrows():
            td = r["trade_date"]
            rows.append({
                "ts_code": r["ts_code"],
                "trade_date": td,
                "open": self._to_decimal(r.get("open")),
                "high": self._to_decimal(r.get("high")),
                "low": self._to_decimal(r.get("low")),
                "close": self._to_decimal(r.get("close")),
                "pre_close": self._to_decimal(r.get("pre_close")),
                "vol": self._to_decimal(r.get("vol")),
                "amount": self._to_decimal(r.get("amount")),
                "pct_chg": self._to_decimal(r.get("pct_chg")),
                "adj_factor": self._to_decimal(adj_map.get(td)),
                "turnover_rate": self._to_decimal(basic_map.get(td)),
                "trade_status": "1",
            })
        return rows

    async def health_check(self) -> bool:
        """验证 token 有效性。"""
        try:
            df = await self._call(
                "trade_cal", exchange="SSE",
                start_date="20240101", end_date="20240101",
            )
            return len(df) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # fetch_raw_* 系列方法 — 按日期获取全市场原始数据
    # ------------------------------------------------------------------

    async def fetch_raw_stock_basic(self, list_status: str = "L") -> list[dict]:
        """获取股票基础信息原始数据。"""
        df = await self._call(
            "stock_basic",
            exchange="",
            list_status=list_status,
            fields="ts_code,symbol,name,area,industry,fullname,enname,cnspell,"
                   "market,exchange,curr_type,list_status,list_date,delist_date,"
                   "is_hs,act_name,act_ent_type",
        )
        return df.to_dict("records")

    async def fetch_raw_trade_cal(
        self, start_date: str, end_date: str, exchange: str = "SSE"
    ) -> list[dict]:
        """获取交易日历原始数据。"""
        df = await self._call(
            "trade_cal",
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_daily(self, trade_date: str) -> list[dict]:
        """按日期获取全市场日线行情原始数据。"""
        df = await self._call("daily", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_adj_factor(self, trade_date: str) -> list[dict]:
        """按日期获取全市场复权因子原始数据。"""
        df = await self._call("adj_factor", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_daily_basic(self, trade_date: str) -> list[dict]:
        """按日期获取全市场每日指标原始数据（PE/PB/换手率/市值等）。"""
        df = await self._call("daily_basic", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_stk_limit(self, trade_date: str) -> list[dict]:
        """按日期获取全市场涨跌停价格原始数据。"""
        df = await self._call("stk_limit", trade_date=trade_date)
        return df.to_dict("records")

    # ------------------------------------------------------------------
    # P1 财务数据 fetch_raw_* 方法 — 按季度获取全市场财务数据
    # ------------------------------------------------------------------

    async def fetch_raw_fina_indicator(self, period: str) -> list[dict]:
        """按季度获取全市场财务指标原始数据（优先使用 VIP 接口）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD，如 20231231 表示 2023 年报

        Returns:
            财务指标原始数据列表
        """
        try:
            # 优先使用 VIP 接口按季度获取全部公司
            df = await self._call("fina_indicator_vip", period=period)
        except Exception as e:
            logger.warning(f"fina_indicator_vip 调用失败，降级到标准接口: {e}")
            # 降级到标准接口（需要逐只股票获取，这里暂不实现）
            raise DataSourceError(f"fina_indicator_vip 不可用，标准接口需逐只股票获取: {e}")
        return df.to_dict("records")

    async def fetch_raw_income(self, period: str) -> list[dict]:
        """按季度获取全市场利润表原始数据（优先使用 VIP 接口）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            利润表原始数据列表
        """
        try:
            df = await self._call("income_vip", period=period)
        except Exception as e:
            logger.warning(f"income_vip 调用失败，降级到标准接口: {e}")
            raise DataSourceError(f"income_vip 不可用，标准接口需逐只股票获取: {e}")
        return df.to_dict("records")

    async def fetch_raw_balancesheet(self, period: str) -> list[dict]:
        """按季度获取全市场资产负债表原始数据（优先使用 VIP 接口）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            资产负债表原始数据列表
        """
        try:
            df = await self._call("balancesheet_vip", period=period)
        except Exception as e:
            logger.warning(f"balancesheet_vip 调用失败，降级到标准接口: {e}")
            raise DataSourceError(f"balancesheet_vip 不可用，标准接口需逐只股票获取: {e}")
        return df.to_dict("records")

    async def fetch_raw_cashflow(self, period: str) -> list[dict]:
        """按季度获取全市场现金流量表原始数据（优先使用 VIP 接口）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            现金流量表原始数据列表
        """
        try:
            df = await self._call("cashflow_vip", period=period)
        except Exception as e:
            logger.warning(f"cashflow_vip 调用失败，降级到标准接口: {e}")
            raise DataSourceError(f"cashflow_vip 不可用，标准接口需逐只股票获取: {e}")
        return df.to_dict("records")

    async def fetch_raw_dividend(self, ann_date: str) -> list[dict]:
        """按公告日期获取分红送股原始数据。

        Args:
            ann_date: 公告日期，格式 YYYYMMDD

        Returns:
            分红送股原始数据列表
        """
        df = await self._call("dividend", ann_date=ann_date)
        return df.to_dict("records")

    async def fetch_raw_forecast(self, period: str) -> list[dict]:
        """按季度获取全市场业绩预告原始数据（优先使用 VIP 接口）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            业绩预告原始数据列表
        """
        try:
            df = await self._call("forecast_vip", period=period)
        except Exception as e:
            logger.warning(f"forecast_vip 调用失败，降级到标准接口: {e}")
            raise DataSourceError(f"forecast_vip 不可用，标准接口需逐只股票获取: {e}")
        return df.to_dict("records")

    async def fetch_raw_express(self, period: str) -> list[dict]:
        """按季度获取全市场业绩快报原始数据（优先使用 VIP 接口）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            业绩快报原始数据列表
        """
        try:
            df = await self._call("express_vip", period=period)
        except Exception as e:
            logger.warning(f"express_vip 调用失败，降级到标准接口: {e}")
            raise DataSourceError(f"express_vip 不可用，标准接口需逐只股票获取: {e}")
        return df.to_dict("records")

    async def fetch_raw_fina_audit(self, period: str) -> list[dict]:
        """按季度获取财务审计意见原始数据。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            财务审计意见原始数据列表
        """
        df = await self._call("fina_audit", period=period)
        return df.to_dict("records")

    async def fetch_raw_fina_mainbz(self, period: str) -> list[dict]:
        """按季度获取全市场主营业务构成原始数据（优先使用 VIP 接口）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            主营业务构成原始数据列表
        """
        try:
            df = await self._call("fina_mainbz_vip", period=period)
        except Exception as e:
            logger.warning(f"fina_mainbz_vip 调用失败，降级到标准接口: {e}")
            raise DataSourceError(f"fina_mainbz_vip 不可用，标准接口需逐只股票获取: {e}")
        return df.to_dict("records")

    async def fetch_raw_disclosure_date(self, end_date: str) -> list[dict]:
        """按报告期获取财报披露计划原始数据。

        Args:
            end_date: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            财报披露计划原始数据列表
        """
        df = await self._call("disclosure_date", end_date=end_date)
        return df.to_dict("records")


    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _call(self, api_name: str, **kwargs) -> pd.DataFrame:
        """调用 Tushare API，带令牌桶限流和重试。

        Args:
            api_name: Tushare 接口名称（如 "daily", "stock_basic"）
            **kwargs: 接口参数

        Returns:
            pandas DataFrame

        Raises:
            DataSourceError: 重试耗尽后仍然失败
        """
        import pandas as _pd

        last_error: Exception | None = None
        for attempt in range(self._retry_count + 1):
            try:
                await self._bucket.acquire()
                df = await asyncio.to_thread(
                    self._pro.query, api_name, **kwargs
                )
                if df is None:
                    return _pd.DataFrame()
                return df
            except Exception as e:
                last_error = e
                if attempt < self._retry_count:
                    wait = self._retry_interval * (2 ** attempt)
                    logger.warning(
                        "Tushare %s 重试 %d/%d (%.1fs 后): %s",
                        api_name, attempt + 1, self._retry_count, wait, e,
                    )
                    await asyncio.sleep(wait)
        raise DataSourceError(
            f"Tushare {api_name} 调用失败（重试 {self._retry_count} 次后）: {last_error}"
        ) from last_error

    @staticmethod
    def _to_decimal(val) -> Decimal | None:
        """将值转换为 Decimal，无效值返回 None。"""
        if val is None:
            return None
        try:
            if isinstance(val, float) and math.isnan(val):
                return None
            return Decimal(str(val))
        except (InvalidOperation, ValueError):
            return None
