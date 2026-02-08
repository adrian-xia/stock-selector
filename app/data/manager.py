import logging
from datetime import date

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.data.client_base import DataSourceClient
from app.data.etl import (
    batch_insert,
    clean_akshare_daily,
    clean_baostock_daily,
    clean_baostock_stock_list,
    clean_baostock_trade_calendar,
)
from app.exceptions import DataSyncError
from app.models.market import Stock, StockDaily, TradeCalendar
from app.models.technical import TechnicalDaily

logger = logging.getLogger(__name__)


class DataManager:
    """Unified data access layer for all data operations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clients: dict[str, DataSourceClient],
        primary: str = "baostock",
    ) -> None:
        self._session_factory = session_factory
        self._clients = clients
        self._primary = primary

    @property
    def _primary_client(self) -> DataSourceClient:
        return self._clients[self._primary]

    @property
    def _backup_clients(self) -> list[tuple[str, DataSourceClient]]:
        return [
            (name, client)
            for name, client in self._clients.items()
            if name != self._primary
        ]

    # --- Sync operations ---

    async def sync_stock_list(self) -> dict:
        """Fetch and persist stock list from data source."""
        async with self._session_factory() as session:
            raw_rows = await self._primary_client.fetch_stock_list()
            cleaned = clean_baostock_stock_list(raw_rows)
            count = await batch_insert(
                session, Stock.__table__, cleaned
            )
            logger.info("Stock list synced: %d records", count)
            return {"inserted": count}

    async def sync_trade_calendar(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict:
        """Fetch and persist trade calendar."""
        if start_date is None:
            start_date = date(1990, 1, 1)
        if end_date is None:
            end_date = date.today()

        async with self._session_factory() as session:
            raw_rows = await self._primary_client.fetch_trade_calendar(
                start_date, end_date
            )
            cleaned = clean_baostock_trade_calendar(raw_rows)
            count = await batch_insert(
                session, TradeCalendar.__table__, cleaned
            )
            logger.info("Trade calendar synced: %d records", count)
            return {"inserted": count}

    async def sync_daily(
        self,
        code: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch daily bars for a single stock with primary/backup fallback."""
        import time

        clean_fn = clean_baostock_daily
        source_name = self._primary

        # 1. API 调用计时
        api_start = time.monotonic()
        try:
            raw_rows = await self._primary_client.fetch_daily(
                code, start_date, end_date
            )
        except Exception as primary_err:
            logger.warning(
                "Primary source (%s) failed for %s: %s",
                self._primary, code, primary_err,
            )
            # Try backup sources
            for backup_name, backup_client in self._backup_clients:
                try:
                    raw_rows = await backup_client.fetch_daily(
                        code, start_date, end_date
                    )
                    clean_fn = clean_akshare_daily
                    source_name = backup_name
                    break
                except Exception as backup_err:
                    logger.warning(
                        "Backup source (%s) failed for %s: %s",
                        backup_name, code, backup_err,
                    )
            else:
                raise DataSyncError(
                    f"All sources failed for {code}"
                ) from primary_err
        api_elapsed = time.monotonic() - api_start

        # 2. 数据清洗计时
        clean_start = time.monotonic()
        cleaned = clean_fn(raw_rows)
        clean_elapsed = time.monotonic() - clean_start

        if not cleaned:
            logger.debug(
                "[sync_daily] %s: API总计=%.2fs, 清洗=%.2fs, 入库=0s (无数据)",
                code, api_elapsed, clean_elapsed,
            )
            return {"inserted": 0, "skipped": 0, "source": source_name}

        # 3. 数据库写入计时
        db_start = time.monotonic()
        async with self._session_factory() as session:
            count = await batch_insert(
                session, StockDaily.__table__, cleaned
            )
        db_elapsed = time.monotonic() - db_start

        # 记录细粒度日志（DEBUG 级别）
        # 注意：api_elapsed 包含连接池等待时间，详细分解见 BaoStockClient 日志
        logger.debug(
            "[sync_daily] %s: API总计=%.2fs, 清洗=%.2fs, 入库=%.2fs",
            code, api_elapsed, clean_elapsed, db_elapsed,
        )

        return {"inserted": count, "source": source_name}

    # --- Query operations ---

    async def get_daily_bars(
        self,
        codes: list[str],
        start_date: date,
        end_date: date,
        adj: str = "qfq",
        fields: list[str] | None = None,
    ) -> pd.DataFrame:
        """Query daily bars with optional forward/backward adjustment."""
        async with self._session_factory() as session:
            stmt = (
                select(StockDaily)
                .where(
                    StockDaily.ts_code.in_(codes),
                    StockDaily.trade_date >= start_date,
                    StockDaily.trade_date <= end_date,
                )
                .order_by(StockDaily.ts_code, StockDaily.trade_date)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        if not rows:
            columns = fields or [
                "ts_code", "trade_date", "open", "high", "low",
                "close", "vol", "amount", "pct_chg", "turnover_rate",
            ]
            return pd.DataFrame(columns=columns)

        records = []
        for r in rows:
            records.append({
                "ts_code": r.ts_code,
                "trade_date": r.trade_date,
                "open": float(r.open) if r.open else None,
                "high": float(r.high) if r.high else None,
                "low": float(r.low) if r.low else None,
                "close": float(r.close) if r.close else None,
                "vol": float(r.vol) if r.vol else 0,
                "amount": float(r.amount) if r.amount else 0,
                "pct_chg": float(r.pct_chg) if r.pct_chg else None,
                "turnover_rate": float(r.turnover_rate) if r.turnover_rate else None,
                "adj_factor": float(r.adj_factor) if r.adj_factor else None,
            })

        df = pd.DataFrame(records)

        # Apply adjustment
        if adj in ("qfq", "hfq") and "adj_factor" in df.columns:
            df = self._apply_adjustment(df, adj)

        if fields:
            available = [f for f in fields if f in df.columns]
            df = df[available]

        return df

    @staticmethod
    def _apply_adjustment(df: pd.DataFrame, adj: str) -> pd.DataFrame:
        """Apply forward or backward price adjustment."""
        if df.empty or "adj_factor" not in df.columns:
            return df

        price_cols = ["open", "high", "low", "close"]

        for code in df["ts_code"].unique():
            mask = df["ts_code"] == code
            code_df = df.loc[mask]
            factors = code_df["adj_factor"]

            if factors.isna().all():
                continue

            if adj == "qfq":
                latest_factor = factors.iloc[-1]
                if latest_factor and latest_factor != 0:
                    for col in price_cols:
                        df.loc[mask, col] = (
                            code_df[col] * factors / latest_factor
                        )
            elif adj == "hfq":
                for col in price_cols:
                    df.loc[mask, col] = code_df[col] * factors

        df = df.drop(columns=["adj_factor"], errors="ignore")
        return df

    async def get_stock_list(
        self, status: str = "L"
    ) -> list[dict]:
        """Query stock list from database."""
        async with self._session_factory() as session:
            stmt = select(Stock).where(Stock.list_status == status)
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [
            {
                "ts_code": r.ts_code,
                "name": r.name,
                "industry": r.industry,
                "market": r.market,
                "list_date": r.list_date,
                "list_status": r.list_status,
            }
            for r in rows
        ]

    async def get_trade_calendar(
        self, start_date: date, end_date: date
    ) -> list[date]:
        """Query trading days in a date range."""
        async with self._session_factory() as session:
            stmt = (
                select(TradeCalendar.cal_date)
                .where(
                    TradeCalendar.is_open.is_(True),
                    TradeCalendar.cal_date >= start_date,
                    TradeCalendar.cal_date <= end_date,
                )
                .order_by(TradeCalendar.cal_date)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    async def is_trade_day(self, d: date) -> bool:
        """Check if a specific date is a trading day."""
        async with self._session_factory() as session:
            stmt = select(TradeCalendar.is_open).where(
                TradeCalendar.cal_date == d
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return bool(row) if row is not None else False

    async def get_latest_technical(
        self,
        codes: list[str],
        trade_date: date | None = None,
        fields: list[str] | None = None,
    ) -> pd.DataFrame:
        """查询指定股票的最新技术指标数据。

        从 technical_daily 表读取预计算的技术指标，供策略引擎消费。

        Args:
            codes: 股票代码列表，如 ["600519.SH", "000001.SZ"]
            trade_date: 指定日期，None 表示查询每只股票的最新记录
            fields: 指标列子集，None 表示返回全部指标列

        Returns:
            包含 ts_code, trade_date 和指标列的 DataFrame
        """
        # 全部指标列名
        all_indicator_cols = [
            "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
            "macd_dif", "macd_dea", "macd_hist",
            "kdj_k", "kdj_d", "kdj_j",
            "rsi6", "rsi12", "rsi24",
            "boll_upper", "boll_mid", "boll_lower",
            "vol_ma5", "vol_ma10", "vol_ratio",
            "atr14",
        ]

        # 确定要查询的列
        select_cols = [TechnicalDaily.ts_code, TechnicalDaily.trade_date]
        if fields:
            # 仅选择指定的指标列
            for f in fields:
                if hasattr(TechnicalDaily, f):
                    select_cols.append(getattr(TechnicalDaily, f))
        else:
            # 选择全部指标列
            for col_name in all_indicator_cols:
                select_cols.append(getattr(TechnicalDaily, col_name))

        async with self._session_factory() as session:
            if trade_date is not None:
                # 查询指定日期的指标
                stmt = (
                    select(*select_cols)
                    .where(
                        TechnicalDaily.ts_code.in_(codes),
                        TechnicalDaily.trade_date == trade_date,
                    )
                )
            else:
                # 查询每只股票的最新记录：使用子查询获取最新 trade_date
                from sqlalchemy import func
                subq = (
                    select(
                        TechnicalDaily.ts_code,
                        func.max(TechnicalDaily.trade_date).label("max_date"),
                    )
                    .where(TechnicalDaily.ts_code.in_(codes))
                    .group_by(TechnicalDaily.ts_code)
                    .subquery()
                )
                stmt = (
                    select(*select_cols)
                    .join(
                        subq,
                        (TechnicalDaily.ts_code == subq.c.ts_code)
                        & (TechnicalDaily.trade_date == subq.c.max_date),
                    )
                )

            result = await session.execute(stmt)
            rows = result.all()

        if not rows:
            # 返回空 DataFrame，保持正确的列结构
            col_names = ["ts_code", "trade_date"]
            if fields:
                col_names.extend(fields)
            else:
                col_names.extend(all_indicator_cols)
            return pd.DataFrame(columns=col_names)

        # 构建 DataFrame
        col_names = [col.key if hasattr(col, "key") else str(col) for col in select_cols]
        records = []
        for row in rows:
            record = {}
            for j, col_name in enumerate(col_names):
                val = row[j]
                if val is not None and col_name not in ("ts_code", "trade_date"):
                    record[col_name] = float(val)
                else:
                    record[col_name] = val
            records.append(record)

        return pd.DataFrame(records)

    async def detect_missing_dates(
        self, start_date: date, end_date: date
    ) -> list[date]:
        """检测指定日期范围内缺失的交易日数据。

        查询交易日历中的交易日，与 stock_daily 表中已有数据的日期对比，
        返回缺失的交易日列表。

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            缺失的交易日列表，按升序排列
        """
        # 1. 查询指定日期范围的交易日
        trading_dates = await self.get_trade_calendar(start_date, end_date)

        if not trading_dates:
            logger.debug(
                "[detect_missing_dates] 日期范围 %s ~ %s 无交易日",
                start_date, end_date,
            )
            return []

        # 2. 查询 stock_daily 表中已有数据的日期（去重）
        async with self._session_factory() as session:
            stmt = (
                select(StockDaily.trade_date)
                .where(
                    StockDaily.trade_date >= start_date,
                    StockDaily.trade_date <= end_date,
                )
                .distinct()
                .order_by(StockDaily.trade_date)
            )
            result = await session.execute(stmt)
            existing_dates = [row[0] for row in result.all()]

        # 3. 计算缺失日期：交易日 - 已有日期
        existing_dates_set = set(existing_dates)
        missing_dates = [
            d for d in trading_dates if d not in existing_dates_set
        ]

        logger.debug(
            "[detect_missing_dates] 日期范围 %s ~ %s: 交易日 %d 天，已有数据 %d 天，缺失 %d 天",
            start_date, end_date,
            len(trading_dates), len(existing_dates), len(missing_dates),
        )

        return missing_dates
