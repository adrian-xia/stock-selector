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
    # P2 资金流向和龙虎榜数据获取
    # ------------------------------------------------------------------

    async def fetch_raw_moneyflow(self, trade_date: str) -> list[dict]:
        """获取个股资金流向原始数据（对应 moneyflow 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            个股资金流向原始数据列表
        """
        df = await self._call("moneyflow", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_moneyflow_dc(self, trade_date: str) -> list[dict]:
        """获取个股资金流向原始数据 - 东方财富（对应 moneyflow_dc 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            东方财富个股资金流向原始数据列表
        """
        df = await self._call("moneyflow_dc", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_moneyflow_ths(self, trade_date: str) -> list[dict]:
        """获取个股资金流向原始数据 - 同花顺（对应 moneyflow_ths 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            同花顺个股资金流向原始数据列表
        """
        df = await self._call("moneyflow_ths", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_moneyflow_hsgt(self, trade_date: str) -> list[dict]:
        """获取沪深港通资金流向原始数据（对应 moneyflow_hsgt 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            沪深港通资金流向原始数据列表
        """
        df = await self._call("moneyflow_hsgt", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_moneyflow_ind_ths(self, trade_date: str) -> list[dict]:
        """获取同花顺行业资金流向原始数据（对应 moneyflow_ind_ths 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            同花顺行业资金流向原始数据列表
        """
        df = await self._call("moneyflow_ind_ths", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_moneyflow_cnt_ths(self, trade_date: str) -> list[dict]:
        """获取同花顺概念板块资金流向原始数据（对应 moneyflow_cnt_ths 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            同花顺概念板块资金流向原始数据列表
        """
        df = await self._call("moneyflow_cnt_ths", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_moneyflow_ind_dc(self, trade_date: str) -> list[dict]:
        """获取东财概念及行业板块资金流向原始数据（对应 moneyflow_ind_dc 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            东财概念及行业板块资金流向原始数据列表
        """
        df = await self._call("moneyflow_ind_dc", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_moneyflow_mkt_dc(self, trade_date: str) -> list[dict]:
        """获取大盘资金流向原始数据 - 东方财富（对应 moneyflow_mkt_dc 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            大盘资金流向原始数据列表
        """
        df = await self._call("moneyflow_mkt_dc", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_top_list(self, trade_date: str) -> list[dict]:
        """获取龙虎榜每日明细原始数据（对应 top_list 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            龙虎榜每日明细原始数据列表
        """
        df = await self._call("top_list", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_top_inst(self, trade_date: str) -> list[dict]:
        """获取龙虎榜机构明细原始数据（对应 top_inst 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD 格式）

        Returns:
            龙虎榜机构明细原始数据列表
        """
        df = await self._call("top_inst", trade_date=trade_date)
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

    # =====================================================================
    # P3 指数数据 fetch_raw_* 方法（16 个）
    # =====================================================================

    async def fetch_raw_index_basic(self, market: str = "") -> list[dict]:
        """获取指数基础信息（对应 index_basic 接口）。

        Args:
            market: 市场类型（SSE/SZSE/MSCI/CSI/CNI），空字符串表示全部

        Returns:
            指数基础信息列表
        """
        df = await self._call("index_basic", api_name="index_basic", market=market)
        return df.to_dict("records")

    async def fetch_raw_index_weight(
        self, index_code: str, trade_date: str
    ) -> list[dict]:
        """获取指数成分股权重（对应 index_weight 接口）。

        Args:
            index_code: 指数代码（如 000300.SH）
            trade_date: 交易日期（YYYYMMDD）

        Returns:
            成分股权重列表
        """
        df = await self._call(
            "index_weight",
            api_name="index_weight",
            index_code=index_code,
            trade_date=trade_date,
        )
        return df.to_dict("records")

    async def fetch_raw_index_daily(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取指数日线行情（对应 index_daily 接口）。

        Args:
            ts_code: 指数代码（如 000300.SH）
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            指数日线行情列表
        """
        df = await self._call(
            "index_daily",
            api_name="index_daily",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_index_weekly(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取指数周线行情（对应 index_weekly 接口）。"""
        df = await self._call(
            "index_weekly",
            api_name="index_weekly",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_index_monthly(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取指数月线行情（对应 index_monthly 接口）。"""
        df = await self._call(
            "index_monthly",
            api_name="index_monthly",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    # __CONTINUE_HERE__
    async def fetch_raw_index_dailybasic(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取指数每日指标（对应 index_dailybasic 接口）。"""
        df = await self._call(
            "index_dailybasic",
            api_name="index_dailybasic",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_index_global(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取国际指数行情（对应 index_global 接口）。"""
        df = await self._call(
            "index_global",
            api_name="index_global",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_daily_info(
        self, trade_date: str, ts_code: str = "", exchange: str = ""
    ) -> list[dict]:
        """获取大盘每日指标（对应 daily_info 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD）
            ts_code: 市场代码（如 000001.SH）
            exchange: 交易所（SSE/SZSE）

        Returns:
            大盘每日指标列表
        """
        df = await self._call(
            "daily_info",
            api_name="daily_info",
            trade_date=trade_date,
            ts_code=ts_code,
            exchange=exchange,
        )
        return df.to_dict("records")

    async def fetch_raw_sz_daily_info(
        self, trade_date: str, ts_code: str = ""
    ) -> list[dict]:
        """获取深圳市场每日指标（对应 sz_daily_info 接口）。"""
        df = await self._call(
            "sz_daily_info",
            api_name="sz_daily_info",
            trade_date=trade_date,
            ts_code=ts_code,
        )
        return df.to_dict("records")

    async def fetch_raw_index_classify(self, level: str = "", src: str = "SW") -> list[dict]:
        """获取申万行业分类（对应 index_classify 接口）。

        Args:
            level: 行业级别（L1/L2/L3）
            src: 分类来源（SW=申万，默认）

        Returns:
            行业分类列表
        """
        df = await self._call(
            "index_classify",
            api_name="index_classify",
            level=level,
            src=src,
        )
        return df.to_dict("records")

    async def fetch_raw_index_member_all(
        self, index_code: str = "", ts_code: str = "", is_new: str = ""
    ) -> list[dict]:
        """获取申万行业成分股（对应 index_member_all 接口）。

        Args:
            index_code: 指数代码（如 801010.SI）
            ts_code: 股票代码（如 600519.SH）
            is_new: 是否最新（Y/N）

        Returns:
            行业成分股列表
        """
        df = await self._call(
            "index_member_all",
            api_name="index_member_all",
            index_code=index_code,
            ts_code=ts_code,
            is_new=is_new,
        )
        return df.to_dict("records")

    async def fetch_raw_sw_daily(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取申万行业日线行情（对应 sw_daily 接口）。"""
        df = await self._call(
            "sw_daily",
            api_name="sw_daily",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_ci_index_member(
        self, index_code: str = "", ts_code: str = ""
    ) -> list[dict]:
        """获取中信行业成分股（对应 ci_index_member 接口）。

        Args:
            index_code: 指数代码（如 CI005001.CI）
            ts_code: 股票代码（如 600519.SH）

        Returns:
            中信行业成分股列表
        """
        df = await self._call(
            "ci_index_member",
            api_name="ci_index_member",
            index_code=index_code,
            ts_code=ts_code,
        )
        return df.to_dict("records")

    async def fetch_raw_ci_daily(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取中信行业日线行情（对应 ci_daily 接口）。"""
        df = await self._call(
            "ci_daily",
            api_name="ci_daily",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_index_factor_pro(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取指数技术面因子（对应 index_factor_pro 接口）。

        包含 MA/MACD/KDJ/RSI/BOLL/ATR/CCI/WR 等技术指标。
        """
        df = await self._call(
            "index_factor_pro",
            api_name="index_factor_pro",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_tdx_daily(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取通达信日线行情（对应 tdx_daily 接口）。"""
        df = await self._call(
            "tdx_daily",
            api_name="tdx_daily",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    # =====================================================================
    # P4 板块数据 fetch_raw_* 方法（8 个）
    # =====================================================================

    async def fetch_raw_ths_index(self) -> list[dict]:
        """获取同花顺板块指数（对应 ths_index 接口）。"""
        df = await self._call("ths_index", api_name="ths_index")
        return df.to_dict("records")

    async def fetch_raw_ths_daily(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> list[dict]:
        """获取同花顺板块日线行情（对应 ths_daily 接口）。"""
        df = await self._call(
            "ths_daily",
            api_name="ths_daily",
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        return df.to_dict("records")

    async def fetch_raw_ths_member(self, ts_code: str) -> list[dict]:
        """获取同花顺板块成分股（对应 ths_member 接口）。

        Args:
            ts_code: 板块代码（如 885720.TI）

        Returns:
            板块成分股列表
        """
        df = await self._call("ths_member", api_name="ths_member", ts_code=ts_code)
        return df.to_dict("records")

    async def fetch_raw_dc_index(self, src: str = "") -> list[dict]:
        """获取东方财富板块指数（对应 dc_index 接口）。

        Args:
            src: 数据源（如 DC 表示东方财富概念板块）

        Returns:
            板块指数列表
        """
        df = await self._call("dc_index", api_name="dc_index", src=src)
        return df.to_dict("records")

    async def fetch_raw_dc_member(self, ts_code: str) -> list[dict]:
        """获取东方财富板块成分股（对应 dc_member 接口）。

        Args:
            ts_code: 板块代码

        Returns:
            板块成分股列表
        """
        df = await self._call("dc_member", api_name="dc_member", ts_code=ts_code)
        return df.to_dict("records")

    async def fetch_raw_dc_hot_new(self, trade_date: str) -> list[dict]:
        """获取东方财富热门板块（对应 dc_hot_new 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD）

        Returns:
            热门板块列表
        """
        df = await self._call("dc_hot_new", api_name="dc_hot_new", trade_date=trade_date)
        return df.to_dict("records")

    async def fetch_raw_tdx_index(self) -> list[dict]:
        """获取通达信板块指数（对应 tdx_index 接口）。"""
        df = await self._call("tdx_index", api_name="tdx_index")
        return df.to_dict("records")

    async def fetch_raw_tdx_member(self, ts_code: str) -> list[dict]:
        """获取通达信板块成分股（对应 tdx_member 接口）。

        Args:
            ts_code: 板块代码

        Returns:
            板块成分股列表
        """
        df = await self._call("tdx_member", api_name="tdx_member", ts_code=ts_code)
        return df.to_dict("records")

    # =====================================================================
    # P5 扩展数据 fetch_raw_* 方法（48 个）
    # =====================================================================

    # 11a. 基础数据补充（7 个）

    async def fetch_raw_namechange(self, ts_code: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取股票曾用名（对应 namechange 接口）。

        Args:
            ts_code: 股票代码
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            股票曾用名列表
        """
        df = await self._call("namechange", api_name="namechange", ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_stock_company(self, ts_code: str = "", exchange: str = "") -> list[dict]:
        """获取上市公司基本信息（对应 stock_company 接口）。

        Args:
            ts_code: 股票代码
            exchange: 交易所（SSE/SZSE）

        Returns:
            上市公司基本信息列表
        """
        df = await self._call("stock_company", api_name="stock_company", ts_code=ts_code, exchange=exchange)
        return df.to_dict("records")

    async def fetch_raw_stk_managers(self, ts_code: str = "", ann_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取上市公司管理层（对应 stk_managers 接口）。

        Args:
            ts_code: 股票代码
            ann_date: 公告日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            上市公司管理层列表
        """
        df = await self._call("stk_managers", api_name="stk_managers", ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_stk_rewards(self, ts_code: str = "", end_date: str = "") -> list[dict]:
        """获取管理层薪酬和持股（对应 stk_rewards 接口）。

        Args:
            ts_code: 股票代码
            end_date: 报告期（YYYYMMDD）

        Returns:
            管理层薪酬和持股列表
        """
        df = await self._call("stk_rewards", api_name="stk_rewards", ts_code=ts_code, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_new_share(self, start_date: str = "", end_date: str = "") -> list[dict]:
        """获取 IPO 新股列表（对应 new_share 接口）。

        Args:
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            IPO 新股列表
        """
        df = await self._call("new_share", api_name="new_share", start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_daily_share(self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取每日股本变动（对应 daily_share 接口）。

        Args:
            ts_code: 股票代码
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            每日股本变动列表
        """
        df = await self._call("daily_share", api_name="daily_share", ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_stk_list_his(self, ts_code: str = "", list_date: str = "", delist_date: str = "") -> list[dict]:
        """获取股票上市历史（对应 stk_list_his 接口）。

        Args:
            ts_code: 股票代码
            list_date: 上市日期（YYYYMMDD）
            delist_date: 退市日期（YYYYMMDD）

        Returns:
            股票上市历史列表
        """
        df = await self._call("stk_list_his", api_name="stk_list_his", ts_code=ts_code, list_date=list_date, delist_date=delist_date)
        return df.to_dict("records")

    # 11b. 行情补充（5 个）

    async def fetch_raw_weekly(self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取周线行情（对应 weekly 接口）。

        Args:
            ts_code: 股票代码
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            周线行情列表
        """
        df = await self._call("weekly", api_name="weekly", ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_monthly(self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取月线行情（对应 monthly 接口）。

        Args:
            ts_code: 股票代码
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            月线行情列表
        """
        df = await self._call("monthly", api_name="monthly", ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_suspend_d(self, ts_code: str = "", suspend_date: str = "", resume_date: str = "") -> list[dict]:
        """获取停复牌信息（对应 suspend_d 接口）。

        Args:
            ts_code: 股票代码
            suspend_date: 停牌日期（YYYYMMDD）
            resume_date: 复牌日期（YYYYMMDD）

        Returns:
            停复牌信息列表
        """
        df = await self._call("suspend_d", api_name="suspend_d", ts_code=ts_code, suspend_date=suspend_date, resume_date=resume_date)
        return df.to_dict("records")

    async def fetch_raw_hsgt_top10(self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = "", market_type: str = "") -> list[dict]:
        """获取沪深港通十大成交股（对应 hsgt_top10 接口）。

        Args:
            ts_code: 股票代码
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            market_type: 市场类型（1=沪股通，3=深股通）

        Returns:
            沪深港通十大成交股列表
        """
        df = await self._call("hsgt_top10", api_name="hsgt_top10", ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, market_type=market_type)
        return df.to_dict("records")

    async def fetch_raw_ggt_daily(self, trade_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取港股通每日成交统计（对应 ggt_daily 接口）。

        Args:
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            港股通每日成交统计列表
        """
        df = await self._call("ggt_daily", api_name="ggt_daily", trade_date=trade_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    # 11c. 市场参考数据（9 个）

    async def fetch_raw_top10_holders(self, ts_code: str = "", period: str = "", ann_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取前十大股东（对应 top10_holders 接口）。"""
        df = await self._call("top10_holders", api_name="top10_holders", ts_code=ts_code, period=period, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_top10_floatholders(self, ts_code: str = "", period: str = "", ann_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取前十大流通股东（对应 top10_floatholders 接口）。"""
        df = await self._call("top10_floatholders", api_name="top10_floatholders", ts_code=ts_code, period=period, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_pledge_stat(self, ts_code: str = "", end_date: str = "") -> list[dict]:
        """获取股权质押统计（对应 pledge_stat 接口）。"""
        df = await self._call("pledge_stat", api_name="pledge_stat", ts_code=ts_code, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_pledge_detail(self, ts_code: str = "", ann_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取股权质押明细（对应 pledge_detail 接口）。"""
        df = await self._call("pledge_detail", api_name="pledge_detail", ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_repurchase(self, ts_code: str = "", ann_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取股票回购（对应 repurchase 接口）。"""
        df = await self._call("repurchase", api_name="repurchase", ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_share_float(self, ts_code: str = "", ann_date: str = "", float_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取限售股解禁（对应 share_float 接口）。"""
        df = await self._call("share_float", api_name="share_float", ts_code=ts_code, ann_date=ann_date, float_date=float_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_block_trade(self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取大宗交易（对应 block_trade 接口）。"""
        df = await self._call("block_trade", api_name="block_trade", ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_stk_holdernumber(self, ts_code: str = "", enddate: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取股东人数（对应 stk_holdernumber 接口）。"""
        df = await self._call("stk_holdernumber", api_name="stk_holdernumber", ts_code=ts_code, enddate=enddate, start_date=start_date, end_date=end_date)
        return df.to_dict("records")

    async def fetch_raw_stk_holdertrade(self, ts_code: str = "", ann_date: str = "", start_date: str = "", end_date: str = "") -> list[dict]:
        """获取股东增减持（对应 stk_holdertrade 接口）。"""
        df = await self._call("stk_holdertrade", api_name="stk_holdertrade", ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return df.to_dict("records")
