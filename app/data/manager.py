import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.data.client_base import DataSourceClient
from app.data.etl import (
    batch_insert,
    transform_tushare_daily,
    transform_tushare_fina_indicator,
    transform_tushare_stock_basic,
    transform_tushare_trade_cal,
)
from app.exceptions import DataSyncError
from app.models.market import FinanceIndicator, Stock, StockDaily, StockSyncProgress, TradeCalendar
from app.models.raw import (
    RawTushareAdjFactor,
    RawTushareDaily,
    RawTushareDailyBasic,
    RawTushareFinaIndicator,
)
from app.models.technical import TechnicalDaily

logger = logging.getLogger(__name__)


class DataManager:
    """Unified data access layer for all data operations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clients: dict[str, DataSourceClient],
        primary: str = "tushare",
    ) -> None:
        self._session_factory = session_factory
        self._clients = clients
        self._primary = primary

    @property
    def _primary_client(self) -> DataSourceClient:
        return self._clients[self._primary]

    # --- Sync operations ---

    async def sync_stock_list(self) -> dict:
        """Fetch and persist stock list from data source."""
        async with self._session_factory() as session:
            raw_rows = await self._primary_client.fetch_stock_list()
            cleaned = transform_tushare_stock_basic(raw_rows)

            # 使用 ON CONFLICT DO UPDATE 确保数据更新
            count = 0
            if cleaned:
                # 每批最多 1000 条，避免参数超限
                batch_size = 1000
                for i in range(0, len(cleaned), batch_size):
                    batch = cleaned[i : i + batch_size]
                    stmt = pg_insert(Stock.__table__).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["ts_code"],
                        set_={
                            "symbol": stmt.excluded.symbol,
                            "name": stmt.excluded.name,
                            "area": stmt.excluded.area,
                            "industry": stmt.excluded.industry,
                            "market": stmt.excluded.market,
                            "list_date": stmt.excluded.list_date,
                            "delist_date": stmt.excluded.delist_date,
                            "list_status": stmt.excluded.list_status,
                        }
                    )
                    await session.execute(stmt)
                    count += len(batch)
                await session.commit()

            logger.info("Stock list synced: %d records", count)
            return {"inserted": count}

    async def sync_trade_calendar(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict:
        """Fetch and persist trade calendar."""
        if start_date is None:
            start_date = date(1990, 1, 1)
        if end_date is None:
            end_date = date.today() + timedelta(days=90)

        async with self._session_factory() as session:
            raw_rows = await self._primary_client.fetch_trade_calendar(
                start_date, end_date
            )
            cleaned = transform_tushare_trade_cal(raw_rows)

            # 使用 ON CONFLICT DO UPDATE 确保数据更新，分批插入避免参数超限
            count = 0
            if cleaned:
                # 每批最多 1000 条（3 列 * 1000 = 3000 参数）
                batch_size = 1000
                for i in range(0, len(cleaned), batch_size):
                    batch = cleaned[i : i + batch_size]
                    stmt = pg_insert(TradeCalendar.__table__).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["cal_date", "exchange"],
                        set_={
                            "is_open": stmt.excluded.is_open,
                            "pre_trade_date": stmt.excluded.pre_trade_date,
                        }
                    )
                    await session.execute(stmt)
                    count += len(batch)
                await session.commit()

            # 计算日期范围
            if cleaned:
                dates = [row["cal_date"] for row in cleaned]
                min_date = min(dates)
                max_date = max(dates)
                logger.info(
                    "Trade calendar synced: %d records (%s to %s)",
                    count, min_date, max_date
                )

                # 检查未来覆盖是否充足
                days_ahead = (max_date - date.today()).days
                if days_ahead < 30:
                    logger.warning(
                        "Trade calendar coverage insufficient: max_date %s is only %d days ahead",
                        max_date, days_ahead
                    )
            else:
                logger.info("Trade calendar synced: %d records", count)

            return {"inserted": count}

    async def sync_daily(
        self,
        code: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch daily bars for a single stock using TushareClient."""
        import time

        # 1. API 调用计时
        api_start = time.monotonic()
        try:
            raw_rows = await self._primary_client.fetch_daily(
                code, start_date, end_date
            )
        except Exception as e:
            raise DataSyncError(
                f"Tushare failed for {code}: {e}"
            ) from e
        api_elapsed = time.monotonic() - api_start

        # 2. 数据清洗计时（fetch_daily 已返回合并后的数据，直接转换）
        clean_start = time.monotonic()
        cleaned = transform_tushare_daily(raw_rows, [], [])
        clean_elapsed = time.monotonic() - clean_start

        if not cleaned:
            logger.debug(
                "[sync_daily] %s: API总计=%.2fs, 清洗=%.2fs, 入库=0s (无数据)",
                code, api_elapsed, clean_elapsed,
            )
            return {"inserted": 0, "skipped": 0, "source": "tushare"}

        # 3. 数据库写入计时
        db_start = time.monotonic()
        async with self._session_factory() as session:
            count = await batch_insert(
                session, StockDaily.__table__, cleaned
            )
        db_elapsed = time.monotonic() - db_start

        logger.debug(
            "[sync_daily] %s: API总计=%.2fs, 清洗=%.2fs, 入库=%.2fs",
            code, api_elapsed, clean_elapsed, db_elapsed,
        )

        return {"inserted": count, "source": "tushare"}

    async def sync_raw_daily(self, trade_date: date) -> dict:
        """按日期获取全市场 daily + adj_factor + daily_basic 写入 raw 表。

        Args:
            trade_date: 交易日期

        Returns:
            {"daily": int, "adj_factor": int, "daily_basic": int}
        """
        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")

        # 并发获取三个接口的数据
        import asyncio
        raw_daily, raw_adj, raw_basic = await asyncio.gather(
            client.fetch_raw_daily(td_str),
            client.fetch_raw_adj_factor(td_str),
            client.fetch_raw_daily_basic(td_str),
        )

        counts = {"daily": 0, "adj_factor": 0, "daily_basic": 0}

        async with self._session_factory() as session:
            if raw_daily:
                counts["daily"] = await self._upsert_raw(
                    session, RawTushareDaily.__table__, raw_daily
                )
            if raw_adj:
                counts["adj_factor"] = await self._upsert_raw(
                    session, RawTushareAdjFactor.__table__, raw_adj
                )
            if raw_basic:
                counts["daily_basic"] = await self._upsert_raw(
                    session, RawTushareDailyBasic.__table__, raw_basic
                )
            await session.commit()

        logger.info(
            "[sync_raw_daily] %s: daily=%d, adj_factor=%d, daily_basic=%d",
            trade_date, counts["daily"], counts["adj_factor"], counts["daily_basic"],
        )
        return counts

    async def etl_daily(self, trade_date: date) -> dict:
        """从 raw 表 JOIN 清洗写入 stock_daily 业务表。

        Args:
            trade_date: 交易日期

        Returns:
            {"inserted": int}
        """
        td_str = trade_date.strftime("%Y%m%d")

        async with self._session_factory() as session:
            # 从 raw 表读取数据
            daily_result = await session.execute(
                select(RawTushareDaily).where(RawTushareDaily.trade_date == td_str)
            )
            raw_daily = [
                {c.key: getattr(r, c.key) for c in RawTushareDaily.__table__.columns if c.key != "fetched_at"}
                for r in daily_result.scalars().all()
            ]

            adj_result = await session.execute(
                select(RawTushareAdjFactor).where(RawTushareAdjFactor.trade_date == td_str)
            )
            raw_adj = [
                {c.key: getattr(r, c.key) for c in RawTushareAdjFactor.__table__.columns if c.key != "fetched_at"}
                for r in adj_result.scalars().all()
            ]

            basic_result = await session.execute(
                select(RawTushareDailyBasic).where(RawTushareDailyBasic.trade_date == td_str)
            )
            raw_basic = [
                {c.key: getattr(r, c.key) for c in RawTushareDailyBasic.__table__.columns if c.key != "fetched_at"}
                for r in basic_result.scalars().all()
            ]

        # ETL 清洗
        cleaned = transform_tushare_daily(raw_daily, raw_adj, raw_basic)

        if not cleaned:
            logger.debug("[etl_daily] %s: 无数据", trade_date)
            return {"inserted": 0}

        # 写入 stock_daily
        async with self._session_factory() as session:
            count = await batch_insert(session, StockDaily.__table__, cleaned)

        logger.info("[etl_daily] %s: 写入 %d 条", trade_date, count)
        return {"inserted": count}

    @staticmethod
    async def _upsert_raw(
        session: AsyncSession, table, rows: list[dict], batch_size: int = 5000
    ) -> int:
        """批量 UPSERT 原始数据到 raw 表（ON CONFLICT DO UPDATE）。"""
        if not rows:
            return 0

        # 获取主键列名
        pk_cols = [c.name for c in table.primary_key.columns]
        # 非主键列用于 UPDATE
        update_cols = [c.name for c in table.columns if c.name not in pk_cols and c.name != "fetched_at"]

        # asyncpg 参数上限 32767
        num_columns = len(rows[0])
        max_batch = 32000 // max(num_columns, 1)
        batch_size = min(batch_size, max_batch)

        total = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            stmt = pg_insert(table).values(batch)
            if update_cols:
                stmt = stmt.on_conflict_do_update(
                    index_elements=pk_cols,
                    set_={col: getattr(stmt.excluded, col) for col in update_cols},
                )
            else:
                stmt = stmt.on_conflict_do_nothing()
            await session.execute(stmt)
            total += len(batch)
        return total

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

    # --- Sync Progress operations ---

    async def reset_stale_status(self) -> int:
        """将 syncing/computing 状态重置为 idle（进程崩溃恢复）。

        重启时不可能还有正在处理的任务，这些状态说明上次进程异常退出。

        Returns:
            重置的记录数
        """
        async with self._session_factory() as session:
            result = await session.execute(
                update(StockSyncProgress)
                .where(StockSyncProgress.status.in_(["syncing", "computing"]))
                .values(status="idle")
            )
            await session.commit()
            count = result.rowcount
            if count > 0:
                logger.info("重置 %d 条 stale 状态记录（syncing/computing → idle）", count)
            return count

    async def init_sync_progress(self) -> dict:
        """为所有未退市股票创建进度记录（INSERT ... ON CONFLICT DO NOTHING）。

        Returns:
            {"total_stocks": int, "new_records": int}
        """
        async with self._session_factory() as session:
            # 查询所有未退市股票的 ts_code
            result = await session.execute(
                select(Stock.ts_code).where(Stock.list_status != "D")
            )
            all_codes = [row[0] for row in result.all()]

            if not all_codes:
                return {"total_stocks": 0, "new_records": 0}

            # 批量 INSERT ... ON CONFLICT DO NOTHING
            new_count = 0
            batch_size = 1000
            for i in range(0, len(all_codes), batch_size):
                batch = all_codes[i : i + batch_size]
                values = [{"ts_code": code} for code in batch]
                stmt = pg_insert(StockSyncProgress.__table__).values(values)
                stmt = stmt.on_conflict_do_nothing(index_elements=["ts_code"])
                result = await session.execute(stmt)
                new_count += result.rowcount
            await session.commit()

        logger.info(
            "进度表初始化完成：总股票 %d，新增记录 %d",
            len(all_codes), new_count,
        )
        return {"total_stocks": len(all_codes), "new_records": new_count}

    async def get_stocks_needing_sync(self, target_date: date) -> list[str]:
        """查询需要同步数据的股票（排除 delisted 和 failed）。

        failed 由 retry job 单独处理，不在常规流程中重试。
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(StockSyncProgress.ts_code).where(
                    StockSyncProgress.status.not_in(["delisted", "failed"]),
                    StockSyncProgress.data_date < target_date,
                )
            )
            return [row[0] for row in result.all()]

    async def get_stocks_needing_indicators(self, target_date: date) -> list[str]:
        """查询需要计算指标的股票（数据已同步但指标未计算）。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(StockSyncProgress.ts_code).where(
                    StockSyncProgress.status.not_in(["delisted", "failed"]),
                    StockSyncProgress.data_date >= target_date,
                    StockSyncProgress.indicator_date < target_date,
                )
            )
            return [row[0] for row in result.all()]

    async def update_data_progress(
        self, ts_code: str, new_data_date: date, session: AsyncSession | None = None
    ) -> None:
        """更新某只股票的 data_date 进度。

        支持传入外部 session 以便在同一事务中操作。
        """
        async def _do(s: AsyncSession) -> None:
            await s.execute(
                update(StockSyncProgress)
                .where(StockSyncProgress.ts_code == ts_code)
                .values(data_date=new_data_date)
            )

        if session is not None:
            await _do(session)
        else:
            async with self._session_factory() as s:
                await _do(s)
                await s.commit()

    async def update_indicator_progress(
        self, ts_code: str, new_indicator_date: date, session: AsyncSession | None = None
    ) -> None:
        """更新某只股票的 indicator_date 进度。"""
        async def _do(s: AsyncSession) -> None:
            await s.execute(
                update(StockSyncProgress)
                .where(StockSyncProgress.ts_code == ts_code)
                .values(indicator_date=new_indicator_date)
            )

        if session is not None:
            await _do(session)
        else:
            async with self._session_factory() as s:
                await _do(s)
                await s.commit()

    async def update_stock_status(
        self, ts_code: str, status: str, error_message: str | None = None
    ) -> None:
        """更新某只股票的同步状态。"""
        values: dict = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        async with self._session_factory() as session:
            await session.execute(
                update(StockSyncProgress)
                .where(StockSyncProgress.ts_code == ts_code)
                .values(**values)
            )
            await session.commit()

    async def get_sync_summary(self, target_date: date) -> dict:
        """获取同步进度摘要（排除 delisted 股票）。

        Returns:
            {total, data_done, indicator_done, failed, completion_rate}
        """
        async with self._session_factory() as session:
            # 排除 delisted 的总数
            total_result = await session.execute(
                select(func.count()).select_from(StockSyncProgress).where(
                    StockSyncProgress.status != "delisted"
                )
            )
            total = total_result.scalar() or 0

            if total == 0:
                return {
                    "total": 0, "data_done": 0, "indicator_done": 0,
                    "failed": 0, "completion_rate": 0.0,
                }

            # data_date >= target_date 的数量
            data_done_result = await session.execute(
                select(func.count()).select_from(StockSyncProgress).where(
                    StockSyncProgress.status != "delisted",
                    StockSyncProgress.data_date >= target_date,
                )
            )
            data_done = data_done_result.scalar() or 0

            # indicator_date >= target_date 的数量
            indicator_done_result = await session.execute(
                select(func.count()).select_from(StockSyncProgress).where(
                    StockSyncProgress.status != "delisted",
                    StockSyncProgress.indicator_date >= target_date,
                )
            )
            indicator_done = indicator_done_result.scalar() or 0

            # failed 数量
            failed_result = await session.execute(
                select(func.count()).select_from(StockSyncProgress).where(
                    StockSyncProgress.status == "failed"
                )
            )
            failed = failed_result.scalar() or 0

            # 完成率 = 数据和指标都完成的股票数 / 总数
            both_done_result = await session.execute(
                select(func.count()).select_from(StockSyncProgress).where(
                    StockSyncProgress.status != "delisted",
                    StockSyncProgress.data_date >= target_date,
                    StockSyncProgress.indicator_date >= target_date,
                )
            )
            both_done = both_done_result.scalar() or 0
            completion_rate = both_done / total

        return {
            "total": total,
            "data_done": data_done,
            "indicator_done": indicator_done,
            "failed": failed,
            "completion_rate": completion_rate,
        }

    async def get_failed_stocks(self, max_retries: int) -> list[dict]:
        """查询可重试的失败股票（retry_count < max_retries）。

        Returns:
            [{"ts_code": str, "data_date": date, "retry_count": int}, ...]
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(
                    StockSyncProgress.ts_code,
                    StockSyncProgress.data_date,
                    StockSyncProgress.retry_count,
                ).where(
                    StockSyncProgress.status == "failed",
                    StockSyncProgress.retry_count < max_retries,
                )
            )
            return [
                {"ts_code": row[0], "data_date": row[1], "retry_count": row[2]}
                for row in result.all()
            ]

    # --- Sync lock (Redis distributed lock) ---

    SYNC_LOCK_KEY = "stock_selector:sync_lock"
    SYNC_LOCK_TTL = 4 * 3600  # 4 小时

    async def acquire_sync_lock(self) -> bool:
        """获取同步锁（Redis SETNX），防止并发执行。

        Redis 不可用时降级为无锁模式（返回 True）。

        Returns:
            True 表示获取成功（或降级无锁），False 表示锁已被占用
        """
        from app.cache.redis_client import get_redis

        redis = get_redis()
        if redis is None:
            logger.warning("[sync_lock] Redis 不可用，降级为无锁模式")
            return True

        try:
            acquired = await redis.set(
                self.SYNC_LOCK_KEY, "1", nx=True, ex=self.SYNC_LOCK_TTL
            )
            if acquired:
                logger.info("[sync_lock] 获取同步锁成功")
                return True
            else:
                logger.warning("[sync_lock] 同步锁已被占用，跳过本次执行")
                return False
        except Exception as e:
            logger.warning("[sync_lock] 获取锁失败（降级无锁模式）: %s", e)
            return True

    async def release_sync_lock(self) -> None:
        """释放同步锁。"""
        from app.cache.redis_client import get_redis

        redis = get_redis()
        if redis is None:
            return

        try:
            await redis.delete(self.SYNC_LOCK_KEY)
            logger.info("[sync_lock] 释放同步锁成功")
        except Exception as e:
            logger.warning("[sync_lock] 释放锁失败: %s", e)

    # --- Delisted stock management ---

    async def mark_stock_delisted(self, ts_code: str, delist_date: date) -> None:
        """标记股票退市：事务中同时更新 stocks 表和 progress 表。"""
        async with self._session_factory() as session:
            # 更新 stocks 表
            await session.execute(
                update(Stock)
                .where(Stock.ts_code == ts_code)
                .values(delist_date=delist_date, list_status="D")
            )
            # 更新 progress 表
            await session.execute(
                update(StockSyncProgress)
                .where(StockSyncProgress.ts_code == ts_code)
                .values(status="delisted")
            )
            await session.commit()

    async def sync_delisted_status(self) -> dict:
        """双向同步退市状态。

        正向：stocks 表中 list_status='D' 但 progress 表中 status!='delisted' → 标记为 delisted
        反向：stocks 表中 list_status!='D' 但 progress 表中 status='delisted' → 恢复为 idle

        Returns:
            {"newly_delisted": int, "restored": int}
        """
        async with self._session_factory() as session:
            # 正向：标记新退市
            result_forward = await session.execute(
                text("""
                    UPDATE stock_sync_progress p
                    SET status = 'delisted'
                    FROM stocks s
                    WHERE p.ts_code = s.ts_code
                      AND s.list_status = 'D'
                      AND p.status != 'delisted'
                """)
            )
            newly_delisted = result_forward.rowcount

            # 反向：恢复取消退市
            result_reverse = await session.execute(
                text("""
                    UPDATE stock_sync_progress p
                    SET status = 'idle'
                    FROM stocks s
                    WHERE p.ts_code = s.ts_code
                      AND s.list_status != 'D'
                      AND p.status = 'delisted'
                """)
            )
            restored = result_reverse.rowcount

            await session.commit()

        if newly_delisted > 0 or restored > 0:
            logger.info(
                "[sync_delisted] 新退市 %d，恢复 %d",
                newly_delisted, restored,
            )
        return {"newly_delisted": newly_delisted, "restored": restored}

    @staticmethod
    def should_have_data(stock: dict, trade_date: date) -> bool:
        """判断股票在指定交易日是否应该有数据。

        基于上市日期和退市日期判断，用于 init_sync_progress 初始过滤。

        Args:
            stock: 股票信息字典，需包含 list_date 和可选的 delist_date
            trade_date: 交易日期

        Returns:
            True 如果该股票在 trade_date 应该有数据
        """
        list_date = stock.get("list_date")
        if list_date and trade_date < list_date:
            return False

        delist_date = stock.get("delist_date")
        if delist_date and trade_date >= delist_date:
            return False

        return True

    # --- Batch sync operations ---

    async def sync_stock_data_in_batches(
        self,
        code: str,
        start_date: date,
        end_date: date,
        batch_days: int = 365,
    ) -> None:
        """按批次拉取单只股票的日线数据。

        每批在事务中完成「批量写入日线数据 + 更新 data_date」，保证原子性。
        单批失败时事务回滚，标记 status='failed'。

        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 目标结束日期
            batch_days: 每批天数（默认 365）
        """
        current_start = start_date
        while current_start <= end_date:
            batch_end = min(current_start + timedelta(days=batch_days - 1), end_date)
            try:
                result = await self.sync_daily(code, current_start, batch_end)
                inserted = result.get("inserted", 0)
                # 仅在实际写入数据时推进 data_date
                if inserted > 0:
                    await self.update_data_progress(code, batch_end)
                logger.debug(
                    "[batch_sync] %s: %s ~ %s 完成，写入 %d 条",
                    code, current_start, batch_end, inserted,
                )
            except Exception as e:
                logger.warning(
                    "[batch_sync] %s: %s ~ %s 失败: %s",
                    code, current_start, batch_end, e,
                )
                await self.update_stock_status(
                    code, "failed", error_message=str(e)[:500]
                )
                raise
            current_start = batch_end + timedelta(days=1)

    async def compute_indicators_in_batches(
        self,
        code: str,
        start_date: date,
        end_date: date,
        batch_days: int = 365,
        lookback_days: int = 300,
    ) -> None:
        """按批次计算单只股票的技术指标。

        每批加载 batch_start - lookback_days 到 batch_end 的数据，
        计算指标后仅写入 batch_start ~ batch_end 范围的结果。
        每批完成后更新 indicator_date。

        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 目标结束日期
            batch_days: 每批天数（默认 365）
            lookback_days: 指标计算回看窗口（默认 300）
        """
        from app.data.indicator import (
            INDICATOR_COLUMNS,
            _build_indicator_row,
            _upsert_technical_rows,
            compute_single_stock_indicators,
        )

        current_start = start_date
        while current_start <= end_date:
            batch_end = min(current_start + timedelta(days=batch_days - 1), end_date)
            # 加载含 lookback 窗口的数据
            load_start = current_start - timedelta(days=lookback_days)

            try:
                async with self._session_factory() as session:
                    stmt = (
                        select(StockDaily)
                        .where(
                            StockDaily.ts_code == code,
                            StockDaily.trade_date >= load_start,
                            StockDaily.trade_date <= batch_end,
                        )
                        .order_by(StockDaily.trade_date.asc())
                    )
                    result = await session.execute(stmt)
                    rows = result.scalars().all()

                if not rows:
                    logger.debug("[batch_indicator] %s: %s ~ %s 无日线数据，跳过指标计算", code, current_start, batch_end)
                    current_start = batch_end + timedelta(days=1)
                    continue

                # 转换为 DataFrame
                records = [{
                    "trade_date": r.trade_date,
                    "open": float(r.open) if r.open else 0.0,
                    "high": float(r.high) if r.high else 0.0,
                    "low": float(r.low) if r.low else 0.0,
                    "close": float(r.close) if r.close else 0.0,
                    "vol": float(r.vol) if r.vol else 0.0,
                } for r in rows]
                df = pd.DataFrame(records)

                # 计算指标
                df_with_indicators = compute_single_stock_indicators(df)

                # 仅取 current_start ~ batch_end 范围的结果
                mask = (
                    (df_with_indicators["trade_date"] >= current_start)
                    & (df_with_indicators["trade_date"] <= batch_end)
                )
                target_rows = df_with_indicators[mask]

                if not target_rows.empty:
                    db_rows = [
                        _build_indicator_row(code, row["trade_date"], row)
                        for _, row in target_rows.iterrows()
                    ]
                    # 写入指标 + 更新 indicator_date 在同一事务中
                    async with self._session_factory() as session:
                        await _upsert_technical_rows(session, db_rows)
                        await self.update_indicator_progress(code, batch_end, session=session)
                        await session.commit()
                else:
                    # target_rows 为空说明该批次无需计算指标，不推进 indicator_date
                    logger.debug(
                        "[batch_indicator] %s: %s ~ %s 无目标行，跳过",
                        code, current_start, batch_end,
                    )

                logger.debug(
                    "[batch_indicator] %s: %s ~ %s 完成，写入 %d 条指标",
                    code, current_start, batch_end, len(target_rows),
                )
            except Exception as e:
                logger.warning(
                    "[batch_indicator] %s: %s ~ %s 失败: %s",
                    code, current_start, batch_end, e,
                )
                await self.update_stock_status(
                    code, "failed", error_message=str(e)[:500]
                )
                raise

            current_start = batch_end + timedelta(days=1)

    # --- Single stock processing ---

    async def process_single_stock(
        self,
        ts_code: str,
        target_date: date,
        data_start_date: date | None = None,
        batch_days: int = 365,
    ) -> None:
        """处理单只股票的完整流程：数据拉取 → 指标计算。

        Args:
            ts_code: 股票代码
            target_date: 目标日期
            data_start_date: 历史数据起始日期（新股首次同步用）
            batch_days: 每批天数
        """
        from app.config import settings

        if data_start_date is None:
            data_start_date = date.fromisoformat(settings.data_start_date)

        # 查询当前进度
        async with self._session_factory() as session:
            result = await session.execute(
                select(StockSyncProgress.data_date, StockSyncProgress.indicator_date)
                .where(StockSyncProgress.ts_code == ts_code)
            )
            row = result.one_or_none()
            if row is None:
                logger.warning("[process_stock] %s 无进度记录，跳过", ts_code)
                return
            current_data_date, current_indicator_date = row

        # 确定数据拉取起始日期
        never_synced = date(1900, 1, 1)
        if current_data_date == never_synced:
            sync_start = data_start_date
        else:
            sync_start = current_data_date + timedelta(days=1)

        # 1. 数据拉取
        if sync_start <= target_date:
            await self.update_stock_status(ts_code, "syncing")
            await self.sync_stock_data_in_batches(
                ts_code, sync_start, target_date, batch_days=batch_days
            )

        # 2. 指标计算
        if current_indicator_date == never_synced:
            indicator_start = data_start_date
        else:
            indicator_start = current_indicator_date + timedelta(days=1)

        if indicator_start <= target_date:
            await self.update_stock_status(ts_code, "computing")
            await self.compute_indicators_in_batches(
                ts_code, indicator_start, target_date, batch_days=batch_days
            )

        # 3. 完成
        await self.update_stock_status(ts_code, "idle")

    async def process_stocks_batch(
        self,
        stocks: list[str],
        target_date: date,
        concurrency: int = 10,
        timeout: int | None = None,
    ) -> dict:
        """批量处理多只股票，带并发控制和超时。

        Args:
            stocks: 股票代码列表
            target_date: 目标日期
            concurrency: 最大并发数
            timeout: 整体超时（秒），None 表示不限

        Returns:
            {"success": int, "failed": int, "timeout": bool}
        """
        import asyncio

        semaphore = asyncio.Semaphore(concurrency)
        success_count = 0
        failed_count = 0
        timed_out = False

        async def _process_one(code: str) -> bool:
            async with semaphore:
                try:
                    await self.process_single_stock(code, target_date)
                    return True
                except Exception as e:
                    logger.warning("[batch_process] %s 处理失败: %s", code, e)
                    return False

        try:
            if timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*[_process_one(c) for c in stocks], return_exceptions=True),
                    timeout=timeout,
                )
            else:
                results = await asyncio.gather(
                    *[_process_one(c) for c in stocks], return_exceptions=True
                )

            for r in results:
                if r is True:
                    success_count += 1
                else:
                    failed_count += 1

        except asyncio.TimeoutError:
            timed_out = True
            logger.warning(
                "[batch_process] 超时（%ds），已处理 %d/%d",
                timeout, success_count + failed_count, len(stocks),
            )

        logger.info(
            "[batch_process] 完成：成功 %d，失败 %d，超时=%s",
            success_count, failed_count, timed_out,
        )
        return {
            "success": success_count,
            "failed": failed_count,
            "timeout": timed_out,
        }

    # ------------------------------------------------------------------
    # P1 财务数据同步和 ETL
    # ------------------------------------------------------------------

    async def sync_raw_fina(self, period: str) -> dict:
        """按季度同步财务数据到 raw 表（仅 fina_indicator，其他财务表待实现）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD，如 20231231 表示 2023 年报

        Returns:
            {"fina_indicator": int} - 各表写入的记录数
        """
        logger.info(f"[sync_raw_fina] 开始同步 {period} 财务数据到 raw 表")

        async with self._session_factory() as session:
            # 1. 同步财务指标（fina_indicator_vip）
            logger.info(f"  - 获取 fina_indicator 数据（period={period}）")
            raw_fina = await self._primary_client.fetch_raw_fina_indicator(period)
            logger.info(f"  - 获取到 {len(raw_fina)} 条 fina_indicator 数据")

            # 批量写入 raw_tushare_fina_indicator
            fina_count = 0
            if raw_fina:
                fina_count = await batch_insert(
                    session, RawTushareFinaIndicator.__table__, raw_fina
                )
                logger.info(f"  - 写入 raw_tushare_fina_indicator: {fina_count} 条")

        logger.info(f"[sync_raw_fina] 完成 {period} 财务数据同步")
        return {"fina_indicator": fina_count}

    async def etl_fina(self, period: str) -> dict:
        """从 raw 表 ETL 清洗财务数据到业务表（仅 finance_indicator，其他财务表待实现）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            {"inserted": int} - 写入的记录数
        """
        logger.info(f"[etl_fina] 开始 ETL 清洗 {period} 财务数据")

        async with self._session_factory() as session:
            # 1. 从 raw_tushare_fina_indicator 读取数据
            result = await session.execute(
                select(RawTushareFinaIndicator).where(
                    RawTushareFinaIndicator.end_date == period
                )
            )
            raw_rows = result.scalars().all()
            logger.info(f"  - 从 raw_tushare_fina_indicator 读取 {len(raw_rows)} 条")

            if not raw_rows:
                logger.warning(f"  - {period} 没有财务指标数据，跳过 ETL")
                return {"inserted": 0}

            # 2. 转换为 dict 格式
            raw_dicts = [
                {
                    "ts_code": r.ts_code,
                    "ann_date": r.ann_date,
                    "end_date": r.end_date,
                    "eps": r.eps,
                    "roe": r.roe,
                    "roe_dt": r.roe_dt,
                    "grossprofit_margin": r.grossprofit_margin,
                    "netprofit_margin": r.netprofit_margin,
                    "or_yoy": r.or_yoy,
                    "netprofit_yoy": r.netprofit_yoy,
                    "current_ratio": r.current_ratio,
                    "quick_ratio": r.quick_ratio,
                    "debt_to_assets": r.debt_to_assets,
                    "ocfps": r.ocfps,
                    "update_flag": r.update_flag,
                }
                for r in raw_rows
            ]

            # 3. ETL 转换
            cleaned = transform_tushare_fina_indicator(raw_dicts)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 批量写入 finance_indicator
            inserted = 0
            if cleaned:
                inserted = await batch_insert(
                    session, FinanceIndicator.__table__, cleaned
                )
                logger.info(f"  - 写入 finance_indicator: {inserted} 条")

        logger.info(f"[etl_fina] 完成 {period} 财务数据 ETL")
        return {"inserted": inserted}

    # =====================================================================
    # P3 指数数据同步方法（5 个）
    # =====================================================================

    async def sync_index_basic(self, market: str = "") -> dict:
        """同步指数基础信息（API → raw → index_basic）。

        Args:
            market: 市场类型（SSE/SZSE/MSCI/CSI/CNI），空字符串表示全部

        Returns:
            同步结果统计
        """
        logger.info(f"[sync_index_basic] 开始同步指数基础信息（market={market or '全部'}）")

        # 1. 从 Tushare 获取原始数据
        raw_data = await self.client.fetch_raw_index_basic(market=market)
        logger.info(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_basic
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexBasic

            raw_inserted = await batch_insert(
                session, RawTushareIndexBasic.__table__, raw_data
            )
            logger.info(f"  - 写入 raw_tushare_index_basic: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_index_basic

            cleaned = transform_tushare_index_basic(raw_data)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 index_basic
            from app.models.index import IndexBasic

            cleaned_inserted = await batch_insert(
                session, IndexBasic.__table__, cleaned
            )
            logger.info(f"  - 写入 index_basic: {cleaned_inserted} 条")

        logger.info(f"[sync_index_basic] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

    # __CONTINUE_HERE__
    async def sync_index_daily(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> dict:
        """同步指数日线行情（API → raw → index_daily）。

        Args:
            ts_code: 指数代码（如 000300.SH）
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            同步结果统计
        """
        logger.info(f"[sync_index_daily] 开始同步指数日线行情")

        # 1. 从 Tushare 获取原始数据
        raw_data = await self.client.fetch_raw_index_daily(
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_daily
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexDaily

            raw_inserted = await batch_insert(
                session, RawTushareIndexDaily.__table__, raw_data
            )
            logger.info(f"  - 写入 raw_tushare_index_daily: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_index_daily

            cleaned = transform_tushare_index_daily(raw_data)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 index_daily
            from app.models.index import IndexDaily

            cleaned_inserted = await batch_insert(
                session, IndexDaily.__table__, cleaned
            )
            logger.info(f"  - 写入 index_daily: {cleaned_inserted} 条")

        logger.info(f"[sync_index_daily] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

    async def sync_index_weight(self, index_code: str, trade_date: str) -> dict:
        """同步指数成分股权重（API → raw → index_weight）。

        Args:
            index_code: 指数代码（如 000300.SH）
            trade_date: 交易日期（YYYYMMDD）

        Returns:
            同步结果统计
        """
        logger.info(f"[sync_index_weight] 开始同步指数成分股权重（{index_code}, {trade_date}）")

        # 1. 从 Tushare 获取原始数据
        raw_data = await self.client.fetch_raw_index_weight(
            index_code=index_code, trade_date=trade_date
        )
        logger.info(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_weight
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexWeight

            raw_inserted = await batch_insert(
                session, RawTushareIndexWeight.__table__, raw_data
            )
            logger.info(f"  - 写入 raw_tushare_index_weight: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_index_weight

            cleaned = transform_tushare_index_weight(raw_data)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 index_weight
            from app.models.index import IndexWeight

            cleaned_inserted = await batch_insert(
                session, IndexWeight.__table__, cleaned
            )
            logger.info(f"  - 写入 index_weight: {cleaned_inserted} 条")

        logger.info(f"[sync_index_weight] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

    async def sync_industry_classify(self, level: str = "", src: str = "SW") -> dict:
        """同步行业分类（API → raw → industry_classify）。

        Args:
            level: 行业级别（L1/L2/L3）
            src: 分类来源（SW=申万，默认）

        Returns:
            同步结果统计
        """
        logger.info(f"[sync_industry_classify] 开始同步行业分类（level={level or '全部'}, src={src}）")

        # 1. 从 Tushare 获取原始数据
        raw_data = await self.client.fetch_raw_index_classify(level=level, src=src)
        logger.info(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_classify
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexClassify

            raw_inserted = await batch_insert(
                session, RawTushareIndexClassify.__table__, raw_data
            )
            logger.info(f"  - 写入 raw_tushare_index_classify: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_industry_classify

            cleaned = transform_tushare_industry_classify(raw_data)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 industry_classify
            from app.models.index import IndustryClassify

            cleaned_inserted = await batch_insert(
                session, IndustryClassify.__table__, cleaned
            )
            logger.info(f"  - 写入 industry_classify: {cleaned_inserted} 条")

        logger.info(f"[sync_industry_classify] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

    async def sync_industry_member(
        self, index_code: str = "", ts_code: str = "", is_new: str = ""
    ) -> dict:
        """同步行业成分股（API → raw → industry_member）。

        Args:
            index_code: 指数代码（如 801010.SI）
            ts_code: 股票代码（如 600519.SH）
            is_new: 是否最新（Y/N）

        Returns:
            同步结果统计
        """
        logger.info(f"[sync_industry_member] 开始同步行业成分股")

        # 1. 从 Tushare 获取原始数据
        raw_data = await self.client.fetch_raw_index_member_all(
            index_code=index_code, ts_code=ts_code, is_new=is_new
        )
        logger.info(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_member_all
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexMemberAll

            raw_inserted = await batch_insert(
                session, RawTushareIndexMemberAll.__table__, raw_data
            )
            logger.info(f"  - 写入 raw_tushare_index_member_all: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_industry_member

            cleaned = transform_tushare_industry_member(raw_data)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 industry_member
            from app.models.index import IndustryMember

            cleaned_inserted = await batch_insert(
                session, IndustryMember.__table__, cleaned
            )
            logger.info(f"  - 写入 industry_member: {cleaned_inserted} 条")

        logger.info(f"[sync_industry_member] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

    # =====================================================================
    # P4 板块数据同步方法（3 个）
    # =====================================================================

    async def sync_concept_index(self, src: str = "THS") -> dict:
        """同步板块基础信息（API → raw → concept_index）。

        统一三个数据源（THS/DC/TDX）到 concept_index 业务表。

        Args:
            src: 数据源（THS=同花顺，DC=东方财富，TDX=通达信）

        Returns:
            同步结果统计
        """
        logger.info(f"[sync_concept_index] 开始同步板块基础信息（src={src}）")

        # 根据数据源选择不同的 fetch 方法和 raw 表
        if src == "THS":
            raw_data = await self._primary_client.fetch_raw_ths_index()
            from app.models.raw import RawTushareThsIndex
            raw_table = RawTushareThsIndex.__table__
        elif src == "DC":
            raw_data = await self._primary_client.fetch_raw_dc_index(src="DC")
            from app.models.raw import RawTushareDcIndex
            raw_table = RawTushareDcIndex.__table__
        elif src == "TDX":
            raw_data = await self._primary_client.fetch_raw_tdx_index()
            from app.models.raw import RawTushareTdxIndex
            raw_table = RawTushareTdxIndex.__table__
        else:
            raise ValueError(f"不支持的数据源: {src}")

        logger.info(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw 表
        async with self._session_factory() as session:
            raw_inserted = await batch_insert(session, raw_table, raw_data)
            logger.info(f"  - 写入 raw 表: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_concept_index
            cleaned = transform_tushare_concept_index(raw_data, src)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 concept_index
            from app.models.concept import ConceptIndex
            cleaned_inserted = await batch_insert(session, ConceptIndex.__table__, cleaned)
            logger.info(f"  - 写入 concept_index: {cleaned_inserted} 条")

        logger.info(f"[sync_concept_index] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

    async def sync_concept_daily(
        self, ts_code: str = "", trade_date: str = "", start_date: str = "", end_date: str = ""
    ) -> dict:
        """同步板块日线行情（API → raw → concept_daily）。

        Args:
            ts_code: 板块代码（如 885720.TI）
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            同步结果统计
        """
        logger.info(f"[sync_concept_daily] 开始同步板块日线行情")

        # 1. 从 Tushare 获取原始数据（使用同花顺数据源）
        raw_data = await self._primary_client.fetch_raw_ths_daily(
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_ths_daily
        async with self._session_factory() as session:
            from app.models.raw import RawTushareThsDaily
            raw_inserted = await batch_insert(session, RawTushareThsDaily.__table__, raw_data)
            logger.info(f"  - 写入 raw_tushare_ths_daily: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_concept_daily
            cleaned = transform_tushare_concept_daily(raw_data)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 concept_daily
            from app.models.concept import ConceptDaily
            cleaned_inserted = await batch_insert(session, ConceptDaily.__table__, cleaned)
            logger.info(f"  - 写入 concept_daily: {cleaned_inserted} 条")

        logger.info(f"[sync_concept_daily] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

    async def sync_concept_member(self, ts_code: str, src: str = "THS") -> dict:
        """同步板块成分股（API → raw → concept_member）。

        Args:
            ts_code: 板块代码
            src: 数据源（THS=同花顺，DC=东方财富，TDX=通达信）

        Returns:
            同步结果统计
        """
        logger.info(f"[sync_concept_member] 开始同步板块成分股（{ts_code}, src={src}）")

        # 根据数据源选择不同的 fetch 方法和 raw 表
        if src == "THS":
            raw_data = await self._primary_client.fetch_raw_ths_member(ts_code)
            from app.models.raw import RawTushareThsMember
            raw_table = RawTushareThsMember.__table__
        elif src == "DC":
            raw_data = await self._primary_client.fetch_raw_dc_member(ts_code)
            from app.models.raw import RawTushareDcMember
            raw_table = RawTushareDcMember.__table__
        elif src == "TDX":
            raw_data = await self._primary_client.fetch_raw_tdx_member(ts_code)
            from app.models.raw import RawTushareTdxMember
            raw_table = RawTushareTdxMember.__table__
        else:
            raise ValueError(f"不支持的数据源: {src}")

        logger.info(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw 表
        async with self._session_factory() as session:
            raw_inserted = await batch_insert(session, raw_table, raw_data)
            logger.info(f"  - 写入 raw 表: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_concept_member
            cleaned = transform_tushare_concept_member(raw_data)
            logger.info(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 concept_member
            from app.models.concept import ConceptMember
            cleaned_inserted = await batch_insert(session, ConceptMember.__table__, cleaned)
            logger.info(f"  - 写入 concept_member: {cleaned_inserted} 条")

        logger.info(f"[sync_concept_member] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

