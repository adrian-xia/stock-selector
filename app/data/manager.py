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
    transform_tushare_index_basic,
    transform_tushare_index_daily,
    transform_tushare_index_technical,
    transform_tushare_index_weight,
    transform_tushare_industry_classify,
    transform_tushare_industry_member,
    transform_tushare_limit_list_d,
    transform_tushare_moneyflow,
    transform_tushare_stock_basic,
    transform_tushare_suspend_d,
    transform_tushare_top_list,
    transform_tushare_trade_cal,
)
from app.exceptions import DataSyncError
from app.models.finance import FinanceIndicator
from app.models.flow import DragonTiger, MoneyFlow
from app.models.index import (
    IndexBasic,
    IndexDaily,
    IndexTechnicalDaily,
    IndexWeight,
    IndustryClassify,
    IndustryMember,
)
from app.models.market import Stock, StockDaily, StockSyncProgress, TradeCalendar
from app.models.raw import (
    RawTushareAdjFactor,
    RawTushareDaily,
    RawTushareDailyBasic,
    RawTushareFinaIndicator,
    RawTushareIndexBasic,
    RawTushareIndexClassify,
    RawTushareIndexDaily,
    RawTushareIndexFactorPro,
    RawTushareIndexMemberAll,
    RawTushareIndexWeight,
    RawTushareMoneyflow,
    RawTushareStockBasic,
    RawTushareTopInst,
    RawTushareTopList,
    RawTushareTradeCal,
    # P5 扩展数据 raw 表
    RawTushareBlockTrade,
    RawTushareDailyShare,
    RawTushareDcHot,
    RawTushareHmBoard,
    RawTushareHmList,
    RawTushareLimitListD,
    RawTushareMargin,
    RawTushareMarginDetail,
    RawTushareMarginTarget,
    RawTushareMonthly,
    RawTushareStkFactor,
    RawTushareStkFactorPro,
    RawTushareStkHoldernumber,
    RawTushareStkHoldertrade,
    RawTushareStockCompany,
    RawTushareSuspendD,
    RawTushareThsHot,
    RawTushareThsLimit,
    RawTushareTop10Floatholders,
    RawTushareTop10Holders,
    RawTushareWeekly,
    # P5 补充数据 raw 表
    RawTushareBrokerRecommend,
    RawTushareCcassHold,
    RawTushareCcassHoldDetail,
    RawTushareCyqChips,
    RawTushareCyqPerf,
    RawTushareGgtDaily,
    RawTushareGgtMonthly,
    RawTushareHkHold,
    RawTushareHmDetail,
    RawTushareHsgtTop10,
    RawTushareKplConcept,
    RawTushareKplList,
    RawTushareLimitStep,
    RawTushareNamechange,
    RawTushareNewShare,
    RawTusharePledgeDetail,
    RawTusharePledgeStat,
    RawTushareRepurchase,
    RawTushareReportRc,
    RawTushareShareFloat,
    RawTushareSlbLen,
    RawTushareStkAuction,
    RawTushareStkAuctionO,
    RawTushareStkListHis,
    RawTushareStkManagers,
    RawTushareStkRewards,
    RawTushareStkSurv,
)
from app.models.extend import LimitListDaily, SuspendInfo
from app.models.technical import TechnicalDaily

logger = logging.getLogger(__name__)

# 核心指数列表：盘后链路每日同步这些指数的日线行情、成分股权重和技术因子
CORE_INDEX_LIST = [
    "000001.SH",  # 上证综指
    "399001.SZ",  # 深证成指
    "399006.SZ",  # 创业板指
    "000300.SH",  # 沪深300
    "000905.SH",  # 中证500
    "000852.SH",  # 中证1000
    "399303.SZ",  # 国证2000
    "000688.SH",  # 科创50
    "000016.SH",  # 上证50
    "399673.SZ",  # 创业板50
]


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
        """Fetch and persist stock list: raw-first (API → raw_tushare_stock_basic → ETL → stocks)."""
        raw_rows = await self._primary_client.fetch_stock_list()

        if not raw_rows:
            logger.warning("[sync_stock_list] 未获取到数据")
            return {"raw_inserted": 0, "inserted": 0}

        # 1. 写入 raw 表
        async with self._session_factory() as session:
            raw_count = await self._upsert_raw(
                session, RawTushareStockBasic.__table__, raw_rows
            )
            await session.commit()

        # 2. ETL 清洗写入 stocks 业务表
        cleaned = transform_tushare_stock_basic(raw_rows)
        count = 0
        if cleaned:
            async with self._session_factory() as session:
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

        logger.info("Stock list synced: raw=%d, business=%d", raw_count, count)
        return {"raw_inserted": raw_count, "inserted": count}

    async def sync_trade_calendar(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> dict:
        """Fetch and persist trade calendar: raw-first (API → raw_tushare_trade_cal → ETL → trade_calendar)."""
        if start_date is None:
            start_date = date(1990, 1, 1)
        if end_date is None:
            end_date = date.today() + timedelta(days=90)

        raw_rows = await self._primary_client.fetch_trade_calendar(
            start_date, end_date
        )

        if not raw_rows:
            logger.warning("[sync_trade_calendar] 未获取到数据")
            return {"raw_inserted": 0, "inserted": 0}

        # 1. 写入 raw 表
        async with self._session_factory() as session:
            raw_count = await self._upsert_raw(
                session, RawTushareTradeCal.__table__, raw_rows
            )
            await session.commit()

        # 2. ETL 清洗写入 trade_calendar 业务表
        cleaned = transform_tushare_trade_cal(raw_rows)
        count = 0
        if cleaned:
            async with self._session_factory() as session:
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

        # 日志：日期范围和覆盖检查
        if cleaned:
            dates = [row["cal_date"] for row in cleaned]
            min_date = min(dates)
            max_date = max(dates)
            logger.info(
                "Trade calendar synced: raw=%d, business=%d (%s to %s)",
                raw_count, count, min_date, max_date
            )
            days_ahead = (max_date - date.today()).days
            if days_ahead < 30:
                logger.warning(
                    "Trade calendar coverage insufficient: max_date %s is only %d days ahead",
                    max_date, days_ahead
                )
        else:
            logger.info("Trade calendar synced: raw=%d, business=%d", raw_count, count)

        return {"raw_inserted": raw_count, "inserted": count}

    async def sync_daily(
        self,
        code: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Fetch daily bars for a single stock, raw-first: API → raw 表 → ETL → stock_daily。"""
        import time

        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]
        sd = start_date.strftime("%Y%m%d")
        ed = end_date.strftime("%Y%m%d")

        # 1. 获取三个接口的原始数据
        api_start = time.monotonic()
        try:
            raw_daily = await client._call("daily", ts_code=code, start_date=sd, end_date=ed)
            raw_adj = await client._call("adj_factor", ts_code=code, start_date=sd, end_date=ed)
            raw_basic = await client._call(
                "daily_basic", ts_code=code, start_date=sd, end_date=ed,
            )
        except Exception as e:
            raise DataSyncError(f"Tushare failed for {code}: {e}") from e
        api_elapsed = time.monotonic() - api_start

        daily_rows = raw_daily.to_dict("records") if not raw_daily.empty else []
        adj_rows = raw_adj.to_dict("records") if not raw_adj.empty else []
        basic_rows = raw_basic.to_dict("records") if not raw_basic.empty else []

        if not daily_rows:
            logger.debug("[sync_daily] %s: API=%.2fs, 无数据", code, api_elapsed)
            return {"inserted": 0, "skipped": 0, "source": "tushare"}

        # 2. 写入 raw 表
        raw_start = time.monotonic()
        async with self._session_factory() as session:
            if daily_rows:
                await self._upsert_raw(session, RawTushareDaily.__table__, daily_rows)
            if adj_rows:
                await self._upsert_raw(session, RawTushareAdjFactor.__table__, adj_rows)
            if basic_rows:
                await self._upsert_raw(session, RawTushareDailyBasic.__table__, basic_rows)
            await session.commit()
        raw_elapsed = time.monotonic() - raw_start

        # 3. ETL: 从原始数据清洗写入 stock_daily
        etl_start = time.monotonic()
        cleaned = transform_tushare_daily(daily_rows, adj_rows, basic_rows)
        if not cleaned:
            return {"inserted": 0, "skipped": 0, "source": "tushare"}

        async with self._session_factory() as session:
            count = await batch_insert(session, StockDaily.__table__, cleaned)
        etl_elapsed = time.monotonic() - etl_start

        logger.debug(
            "[sync_daily] %s: API=%.2fs, raw=%.2fs, ETL=%.2fs, 写入 %d 条",
            code, api_elapsed, raw_elapsed, etl_elapsed, count,
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

        logger.debug("[etl_daily] %s: 写入 %d 条", trade_date, count)
        return {"inserted": count}

    # --- P2 资金流向同步 ---

    async def sync_raw_moneyflow(self, trade_date: date) -> dict:
        """按日期获取全市场个股资金流向写入 raw 表。

        Args:
            trade_date: 交易日期

        Returns:
            {"moneyflow": int}
        """
        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")

        raw_moneyflow = await client.fetch_raw_moneyflow(td_str)

        counts = {"moneyflow": 0}
        async with self._session_factory() as session:
            if raw_moneyflow:
                counts["moneyflow"] = await self._upsert_raw(
                    session, RawTushareMoneyflow.__table__, raw_moneyflow
                )
            await session.commit()

        logger.debug(
            "[sync_raw_moneyflow] %s: moneyflow=%d",
            trade_date, counts["moneyflow"],
        )
        return counts

    async def sync_raw_top_list(self, trade_date: date) -> dict:
        """按日期获取龙虎榜明细和机构明细写入 raw 表。

        Args:
            trade_date: 交易日期

        Returns:
            {"top_list": int, "top_inst": int}
        """
        import asyncio

        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")

        raw_top_list, raw_top_inst = await asyncio.gather(
            client.fetch_raw_top_list(td_str),
            client.fetch_raw_top_inst(td_str),
        )

        counts = {"top_list": 0, "top_inst": 0}
        async with self._session_factory() as session:
            if raw_top_list:
                counts["top_list"] = await self._upsert_raw(
                    session, RawTushareTopList.__table__, raw_top_list
                )
            if raw_top_inst:
                counts["top_inst"] = await self._upsert_raw(
                    session, RawTushareTopInst.__table__, raw_top_inst
                )
            await session.commit()

        logger.debug(
            "[sync_raw_top_list] %s: top_list=%d, top_inst=%d",
            trade_date, counts["top_list"], counts["top_inst"],
        )
        return counts

    async def etl_moneyflow(self, trade_date: date) -> dict:
        """从 raw 表读取资金流向和龙虎榜数据，清洗后写入业务表。

        Args:
            trade_date: 交易日期

        Returns:
            {"money_flow": int, "dragon_tiger": int}
        """
        td_str = trade_date.strftime("%Y%m%d")

        async with self._session_factory() as session:
            # 读取 raw_tushare_moneyflow
            mf_result = await session.execute(
                select(RawTushareMoneyflow).where(
                    RawTushareMoneyflow.trade_date == td_str
                )
            )
            raw_mf = [
                {c.key: getattr(r, c.key) for c in RawTushareMoneyflow.__table__.columns if c.key != "fetched_at"}
                for r in mf_result.scalars().all()
            ]

            # 读取 raw_tushare_top_list
            tl_result = await session.execute(
                select(RawTushareTopList).where(
                    RawTushareTopList.trade_date == td_str
                )
            )
            raw_tl = [
                {c.key: getattr(r, c.key) for c in RawTushareTopList.__table__.columns if c.key != "fetched_at"}
                for r in tl_result.scalars().all()
            ]

        # ETL 清洗
        cleaned_mf = transform_tushare_moneyflow(raw_mf)
        cleaned_tl = transform_tushare_top_list(raw_tl)

        counts = {"money_flow": 0, "dragon_tiger": 0}

        async with self._session_factory() as session:
            if cleaned_mf:
                counts["money_flow"] = await batch_insert(
                    session, MoneyFlow.__table__, cleaned_mf
                )
            if cleaned_tl:
                counts["dragon_tiger"] = await batch_insert(
                    session, DragonTiger.__table__, cleaned_tl
                )

        logger.debug(
            "[etl_moneyflow] %s: money_flow=%d, dragon_tiger=%d",
            trade_date, counts["money_flow"], counts["dragon_tiger"],
        )
        return counts

    # --- P3 指数数据同步 ---

    async def sync_raw_index_daily(self, trade_date: date, *, end_date: date | None = None) -> dict:
        """按日期获取核心指数日线行情写入 raw 表。

        支持两种模式：
        - 单日模式：只传 trade_date（盘后增量用）
        - 批量模式：传 trade_date + end_date（全量初始化用，每个指数 1 次 API 调用）

        Args:
            trade_date: 起始日期（单日模式时也是结束日期）
            end_date: 结束日期（批量模式），None 表示单日模式

        Returns:
            {"index_daily": int}
        """
        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]
        start_str = trade_date.strftime("%Y%m%d")
        end_str = (end_date or trade_date).strftime("%Y%m%d")

        all_rows: list[dict] = []
        for ts_code in CORE_INDEX_LIST:
            rows = await client.fetch_raw_index_daily(
                ts_code=ts_code, start_date=start_str, end_date=end_str
            )
            all_rows.extend(rows)

        counts = {"index_daily": 0}
        async with self._session_factory() as session:
            if all_rows:
                counts["index_daily"] = await self._upsert_raw(
                    session, RawTushareIndexDaily.__table__, all_rows
                )
            await session.commit()

        label = f"{trade_date}~{end_date}" if end_date else str(trade_date)
        logger.debug("[sync_raw_index_daily] %s: index_daily=%d", label, counts["index_daily"])
        return counts

    async def sync_raw_index_weight(self, trade_date: date, *, end_date: date | None = None) -> dict:
        """按日期获取核心指数成分股权重写入 raw 表。

        支持两种模式：
        - 单日模式：只传 trade_date（盘后增量用）
        - 批量模式：传 trade_date + end_date（全量初始化用，每个指数 1 次 API 调用）

        Args:
            trade_date: 起始日期（单日模式时也是结束日期）
            end_date: 结束日期（批量模式），None 表示单日模式

        Returns:
            {"index_weight": int}
        """
        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]
        start_str = trade_date.strftime("%Y%m%d")
        end_str = (end_date or trade_date).strftime("%Y%m%d")

        all_rows: list[dict] = []
        for ts_code in CORE_INDEX_LIST:
            if end_date:
                rows = await client.fetch_raw_index_weight(
                    index_code=ts_code, start_date=start_str, end_date=end_str
                )
            else:
                rows = await client.fetch_raw_index_weight(
                    index_code=ts_code, trade_date=start_str
                )
            all_rows.extend(rows)

        counts = {"index_weight": 0}
        async with self._session_factory() as session:
            if all_rows:
                counts["index_weight"] = await self._upsert_raw(
                    session, RawTushareIndexWeight.__table__, all_rows
                )
            await session.commit()

        label = f"{trade_date}~{end_date}" if end_date else str(trade_date)
        logger.debug("[sync_raw_index_weight] %s: index_weight=%d", label, counts["index_weight"])
        return counts

    async def sync_raw_index_technical(self, trade_date: date, *, end_date: date | None = None) -> dict:
        """按日期获取核心指数技术因子写入 raw 表。

        支持两种模式：
        - 单日模式：只传 trade_date，按单日获取（盘后增量用）
        - 批量模式：传 trade_date + end_date，按日期范围批量获取（全量初始化用，
          每个指数只需 1 次 API 调用，大幅节省 idx_factor_pro 每日限额）

        注意：idx_factor_pro 接口可能需要 VIP 权限，不可用时跳过。

        Args:
            trade_date: 起始日期（单日模式时也是结束日期）
            end_date: 结束日期（批量模式），None 表示单日模式

        Returns:
            {"idx_factor_pro": int}
        """
        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]
        start_str = trade_date.strftime("%Y%m%d")
        end_str = (end_date or trade_date).strftime("%Y%m%d")

        all_rows: list[dict] = []
        try:
            for ts_code in CORE_INDEX_LIST:
                rows = await client.fetch_raw_index_factor_pro(
                    ts_code, start_date=start_str, end_date=end_str
                )
                all_rows.extend(rows)
        except Exception as e:
            logger.warning("[sync_raw_index_technical] idx_factor_pro 接口不可用（可能需要 VIP 权限），跳过: %s", e)
            return {"idx_factor_pro": 0}

        counts = {"idx_factor_pro": 0}
        async with self._session_factory() as session:
            if all_rows:
                counts["idx_factor_pro"] = await self._upsert_raw(
                    session, RawTushareIndexFactorPro.__table__, all_rows
                )
            await session.commit()

        label = f"{trade_date}~{end_date}" if end_date else str(trade_date)
        logger.debug("[sync_raw_index_technical] %s: idx_factor_pro=%d", label, counts["idx_factor_pro"])
        return counts

    # --- P3 指数静态数据同步 ---

    async def sync_raw_index_basic(self) -> dict:
        """全量获取指数基础信息写入 raw 表。

        Returns:
            {"index_basic": int}
        """
        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_rows = await client.fetch_raw_index_basic()

        counts = {"index_basic": 0}
        async with self._session_factory() as session:
            if raw_rows:
                counts["index_basic"] = await self._upsert_raw(
                    session, RawTushareIndexBasic.__table__, raw_rows
                )
            await session.commit()

        logger.debug("[sync_raw_index_basic] index_basic=%d", counts["index_basic"])
        return counts

    async def sync_raw_industry_classify(self) -> dict:
        """全量获取行业分类写入 raw 表。

        分别获取 SW（旧版）和 SW2021（新版）申万行业分类并合并。

        Returns:
            {"index_classify": int}
        """
        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]

        # 获取不同版本的申万行业分类（不传 level，全量获取）
        raw_rows: list[dict] = []
        for src in ["SW", "SW2021"]:
            try:
                rows = await client.fetch_raw_index_classify(level="", src=src)
                raw_rows.extend(rows)
            except Exception as e:
                logger.warning("[sync_raw_industry_classify] src=%s 获取失败: %s", src, e)

        if not raw_rows:
            logger.warning("[sync_raw_industry_classify] 所有来源均返回 0 行（可能是接口权限限制）")

        counts = {"index_classify": 0}
        async with self._session_factory() as session:
            if raw_rows:
                counts["index_classify"] = await self._upsert_raw(
                    session, RawTushareIndexClassify.__table__, raw_rows
                )
            await session.commit()

        logger.debug("[sync_raw_industry_classify] index_classify=%d", counts["index_classify"])
        return counts

    async def sync_raw_industry_member(self) -> dict:
        """全量获取行业成分股写入 raw 表。

        fetch_raw_index_member_all 已内置 offset/limit 分页，直接调用即可。

        Returns:
            {"index_member_all": int}
        """
        from app.data.tushare import TushareClient

        client: TushareClient = self._primary_client  # type: ignore[assignment]

        raw_rows = await client.fetch_raw_index_member_all()

        counts = {"index_member_all": 0}
        async with self._session_factory() as session:
            if raw_rows:
                counts["index_member_all"] = await self._upsert_raw(
                    session, RawTushareIndexMemberAll.__table__, raw_rows
                )
            await session.commit()

        logger.debug("[sync_raw_industry_member] index_member_all=%d", counts["index_member_all"])
        return counts

    # --- P3 指数数据 ETL ---

    async def etl_index(self, trade_date: date) -> dict:
        """从 raw 表清洗指数日线、成分股权重和技术因子写入业务表。

        Args:
            trade_date: 交易日期

        Returns:
            {"index_daily": int, "index_weight": int, "index_technical_daily": int}
        """
        td_str = trade_date.strftime("%Y%m%d")

        async with self._session_factory() as session:
            # 读取 raw_tushare_index_daily
            id_result = await session.execute(
                select(RawTushareIndexDaily).where(RawTushareIndexDaily.trade_date == td_str)
            )
            raw_id = [
                {c.key: getattr(r, c.key) for c in RawTushareIndexDaily.__table__.columns if c.key != "fetched_at"}
                for r in id_result.scalars().all()
            ]

            # 读取 raw_tushare_index_weight
            iw_result = await session.execute(
                select(RawTushareIndexWeight).where(RawTushareIndexWeight.trade_date == td_str)
            )
            raw_iw = [
                {c.key: getattr(r, c.key) for c in RawTushareIndexWeight.__table__.columns if c.key != "fetched_at"}
                for r in iw_result.scalars().all()
            ]

            # 读取 raw_tushare_index_factor_pro
            it_result = await session.execute(
                select(RawTushareIndexFactorPro).where(RawTushareIndexFactorPro.trade_date == td_str)
            )
            raw_it = [
                {c.key: getattr(r, c.key) for c in RawTushareIndexFactorPro.__table__.columns if c.key != "fetched_at"}
                for r in it_result.scalars().all()
            ]

        # ETL 清洗
        cleaned_id = transform_tushare_index_daily(raw_id)
        cleaned_iw = transform_tushare_index_weight(raw_iw)
        cleaned_it = transform_tushare_index_technical(raw_it)

        counts = {"index_daily": 0, "index_weight": 0, "index_technical_daily": 0}
        async with self._session_factory() as session:
            if cleaned_id:
                counts["index_daily"] = await batch_insert(
                    session, IndexDaily.__table__, cleaned_id
                )
            if cleaned_iw:
                counts["index_weight"] = await batch_insert(
                    session, IndexWeight.__table__, cleaned_iw
                )
            if cleaned_it:
                counts["index_technical_daily"] = await batch_insert(
                    session, IndexTechnicalDaily.__table__, cleaned_it
                )

        logger.debug(
            "[etl_index] %s: index_daily=%d, index_weight=%d, index_technical_daily=%d",
            trade_date, counts["index_daily"], counts["index_weight"], counts["index_technical_daily"],
        )
        return counts

    async def etl_index_static(self) -> dict:
        """从 raw 表清洗指数基础信息、行业分类和行业成分股写入业务表。

        Returns:
            {"index_basic": int, "industry_classify": int, "industry_member": int}
        """
        async with self._session_factory() as session:
            # 读取 raw_tushare_index_basic
            ib_result = await session.execute(select(RawTushareIndexBasic))
            raw_ib = [
                {c.key: getattr(r, c.key) for c in RawTushareIndexBasic.__table__.columns if c.key != "fetched_at"}
                for r in ib_result.scalars().all()
            ]

            # 读取 raw_tushare_index_classify
            ic_result = await session.execute(select(RawTushareIndexClassify))
            raw_ic = [
                {c.key: getattr(r, c.key) for c in RawTushareIndexClassify.__table__.columns if c.key != "fetched_at"}
                for r in ic_result.scalars().all()
            ]

            # 读取 raw_tushare_index_member_all
            im_result = await session.execute(select(RawTushareIndexMemberAll))
            raw_im = [
                {c.key: getattr(r, c.key) for c in RawTushareIndexMemberAll.__table__.columns if c.key != "fetched_at"}
                for r in im_result.scalars().all()
            ]

        # ETL 清洗
        cleaned_ib = transform_tushare_index_basic(raw_ib)
        cleaned_ic = transform_tushare_industry_classify(raw_ic)
        cleaned_im = transform_tushare_industry_member(raw_im)

        counts = {"index_basic": 0, "industry_classify": 0, "industry_member": 0}
        async with self._session_factory() as session:
            if cleaned_ib:
                counts["index_basic"] = await batch_insert(
                    session, IndexBasic.__table__, cleaned_ib
                )
            if cleaned_ic:
                counts["industry_classify"] = await batch_insert(
                    session, IndustryClassify.__table__, cleaned_ic
                )
            if cleaned_im:
                counts["industry_member"] = await batch_insert(
                    session, IndustryMember.__table__, cleaned_im
                )

        logger.debug(
            "[etl_index_static] index_basic=%d, industry_classify=%d, industry_member=%d",
            counts["index_basic"], counts["industry_classify"], counts["industry_member"],
        )
        return counts

    @staticmethod
    async def _upsert_raw(
        session: AsyncSession, table, rows: list[dict], batch_size: int = 5000
    ) -> int:
        """批量 UPSERT 原始数据到 raw 表，优先使用 COPY 协议。"""
        if not rows:
            return 0

        import math

        # 清洗 NaN → None（Tushare 返回的 DataFrame 转 dict 后 NaN 为 float('nan')）
        for row in rows:
            for k, v in row.items():
                if isinstance(v, float) and math.isnan(v):
                    row[k] = None

        # 按主键去重（保留最后一条，避免 ON CONFLICT 同批次重复行报错）
        pk_cols = [c.name for c in table.primary_key.columns]
        if pk_cols:
            # 过滤主键为 None 的行
            rows = [r for r in rows if all(r.get(c) is not None for c in pk_cols)]
            seen = {}
            for row in rows:
                key = tuple(row.get(c) for c in pk_cols)
                seen[key] = row
            rows = list(seen.values())

        # 过滤掉表中不存在的列（Tushare API 可能返回额外字段）
        valid_cols = {c.name for c in table.columns}
        rows = [{k: v for k, v in row.items() if k in valid_cols} for row in rows]

        # 优先尝试 COPY 协议
        try:
            from app.data.copy_writer import copy_insert
            return await copy_insert(table, rows, conflict="update")
        except Exception as e:
            logger.warning(
                "[_upsert_raw] COPY 协议写入 %s 失败，降级到 INSERT: %s",
                table.name, e,
            )

        # Fallback: 原有 INSERT ... ON CONFLICT DO UPDATE
        pk_cols = [c.name for c in table.primary_key.columns]
        update_cols = [c.name for c in table.columns if c.name not in pk_cols and c.name != "fetched_at"]

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
            "raw_summary": await self._get_raw_sync_summary(target_date),
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
        logger.debug(f"[sync_raw_fina] 开始同步 {period} 财务数据到 raw 表")

        async with self._session_factory() as session:
            # 1. 同步财务指标（fina_indicator_vip）
            logger.debug(f"  - 获取 fina_indicator 数据（period={period}）")
            raw_fina = await self._primary_client.fetch_raw_fina_indicator(period)
            logger.debug(f"  - 获取到 {len(raw_fina)} 条 fina_indicator 数据")

            # 批量写入 raw_tushare_fina_indicator
            fina_count = 0
            if raw_fina:
                fina_count = await batch_insert(
                    session, RawTushareFinaIndicator.__table__, raw_fina
                )
                logger.debug(f"  - 写入 raw_tushare_fina_indicator: {fina_count} 条")

        # 更新 raw_sync_progress
        if fina_count > 0:
            from datetime import date as _date
            # period 格式 YYYYMMDD，转为 date
            sync_date = _date(int(period[:4]), int(period[4:6]), int(period[6:8]))
            await self._update_raw_sync_progress(
                "raw_tushare_fina_indicator", sync_date, fina_count
            )

        logger.debug(f"[sync_raw_fina] 完成 {period} 财务数据同步")
        return {"fina_indicator": fina_count}

    async def etl_fina(self, period: str) -> dict:
        """从 raw 表 ETL 清洗财务数据到业务表（仅 finance_indicator，其他财务表待实现）。

        Args:
            period: 报告期（季度最后一天），格式 YYYYMMDD

        Returns:
            {"inserted": int} - 写入的记录数
        """
        logger.debug(f"[etl_fina] 开始 ETL 清洗 {period} 财务数据")

        async with self._session_factory() as session:
            # 1. 从 raw_tushare_fina_indicator 读取数据
            result = await session.execute(
                select(RawTushareFinaIndicator).where(
                    RawTushareFinaIndicator.end_date == period
                )
            )
            raw_rows = result.scalars().all()
            logger.debug(f"  - 从 raw_tushare_fina_indicator 读取 {len(raw_rows)} 条")

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
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 批量写入 finance_indicator
            inserted = 0
            if cleaned:
                inserted = await batch_insert(
                    session, FinanceIndicator.__table__, cleaned
                )
                logger.debug(f"  - 写入 finance_indicator: {inserted} 条")

        logger.debug(f"[etl_fina] 完成 {period} 财务数据 ETL")
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
        logger.debug(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_basic
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexBasic

            raw_inserted = await batch_insert(
                session, RawTushareIndexBasic.__table__, raw_data
            )
            logger.debug(f"  - 写入 raw_tushare_index_basic: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_index_basic

            cleaned = transform_tushare_index_basic(raw_data)
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 index_basic
            from app.models.index import IndexBasic

            cleaned_inserted = await batch_insert(
                session, IndexBasic.__table__, cleaned
            )
            logger.debug(f"  - 写入 index_basic: {cleaned_inserted} 条")

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
        logger.debug(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_daily
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexDaily

            raw_inserted = await batch_insert(
                session, RawTushareIndexDaily.__table__, raw_data
            )
            logger.debug(f"  - 写入 raw_tushare_index_daily: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_index_daily

            cleaned = transform_tushare_index_daily(raw_data)
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 index_daily
            from app.models.index import IndexDaily

            cleaned_inserted = await batch_insert(
                session, IndexDaily.__table__, cleaned
            )
            logger.debug(f"  - 写入 index_daily: {cleaned_inserted} 条")

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
        logger.debug(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_weight
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexWeight

            raw_inserted = await batch_insert(
                session, RawTushareIndexWeight.__table__, raw_data
            )
            logger.debug(f"  - 写入 raw_tushare_index_weight: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_index_weight

            cleaned = transform_tushare_index_weight(raw_data)
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 index_weight
            from app.models.index import IndexWeight

            cleaned_inserted = await batch_insert(
                session, IndexWeight.__table__, cleaned
            )
            logger.debug(f"  - 写入 index_weight: {cleaned_inserted} 条")

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
        logger.debug(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_classify
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexClassify

            raw_inserted = await batch_insert(
                session, RawTushareIndexClassify.__table__, raw_data
            )
            logger.debug(f"  - 写入 raw_tushare_index_classify: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_industry_classify

            cleaned = transform_tushare_industry_classify(raw_data)
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 industry_classify
            from app.models.index import IndustryClassify

            cleaned_inserted = await batch_insert(
                session, IndustryClassify.__table__, cleaned
            )
            logger.debug(f"  - 写入 industry_classify: {cleaned_inserted} 条")

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
        logger.debug(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_index_member_all
        async with self.session_factory() as session:
            from app.models.raw import RawTushareIndexMemberAll

            raw_inserted = await batch_insert(
                session, RawTushareIndexMemberAll.__table__, raw_data
            )
            logger.debug(f"  - 写入 raw_tushare_index_member_all: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_industry_member

            cleaned = transform_tushare_industry_member(raw_data)
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 industry_member
            from app.models.index import IndustryMember

            cleaned_inserted = await batch_insert(
                session, IndustryMember.__table__, cleaned
            )
            logger.debug(f"  - 写入 industry_member: {cleaned_inserted} 条")

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

        logger.debug(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw 表
        async with self._session_factory() as session:
            raw_inserted = await batch_insert(session, raw_table, raw_data)
            logger.debug(f"  - 写入 raw 表: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_concept_index
            cleaned = transform_tushare_concept_index(raw_data, src)
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 concept_index
            from app.models.concept import ConceptIndex
            cleaned_inserted = await batch_insert(session, ConceptIndex.__table__, cleaned)
            logger.debug(f"  - 写入 concept_index: {cleaned_inserted} 条")

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
        logger.debug(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw_tushare_ths_daily
        async with self._session_factory() as session:
            from app.models.raw import RawTushareThsDaily
            raw_inserted = await batch_insert(session, RawTushareThsDaily.__table__, raw_data)
            logger.debug(f"  - 写入 raw_tushare_ths_daily: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_concept_daily
            cleaned = transform_tushare_concept_daily(raw_data)
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 concept_daily
            from app.models.concept import ConceptDaily
            cleaned_inserted = await batch_insert(session, ConceptDaily.__table__, cleaned)
            logger.debug(f"  - 写入 concept_daily: {cleaned_inserted} 条")

        # 更新 raw_sync_progress
        if raw_inserted > 0 and trade_date:
            from datetime import date as _date
            td = trade_date.replace("-", "") if "-" in trade_date else trade_date
            sync_date = _date(int(td[:4]), int(td[4:6]), int(td[6:8]))
            await self._update_raw_sync_progress(
                "raw_tushare_ths_daily", sync_date, raw_inserted
            )

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

        logger.debug(f"  - 从 Tushare 获取 {len(raw_data)} 条原始数据")

        if not raw_data:
            logger.warning("  - 未获取到数据")
            return {"raw_inserted": 0, "cleaned_inserted": 0}

        # 2. 写入 raw 表
        async with self._session_factory() as session:
            raw_inserted = await batch_insert(session, raw_table, raw_data)
            logger.debug(f"  - 写入 raw 表: {raw_inserted} 条")

            # 3. ETL 转换
            from app.data.etl import transform_tushare_concept_member
            cleaned = transform_tushare_concept_member(raw_data)
            logger.debug(f"  - ETL 转换得到 {len(cleaned)} 条清洗数据")

            # 4. 写入 concept_member
            from app.models.concept import ConceptMember
            cleaned_inserted = await batch_insert(session, ConceptMember.__table__, cleaned)
            logger.debug(f"  - 写入 concept_member: {cleaned_inserted} 条")

        # 更新 raw_sync_progress
        if raw_inserted > 0:
            from datetime import date as _date
            raw_table_name = {
                "THS": "raw_tushare_ths_member",
                "DC": "raw_tushare_dc_member",
                "TDX": "raw_tushare_tdx_member",
            }.get(src, "raw_tushare_ths_member")
            await self._update_raw_sync_progress(
                raw_table_name, _date.today(), raw_inserted
            )

        logger.info(f"[sync_concept_member] 完成")
        return {"raw_inserted": raw_inserted, "cleaned_inserted": cleaned_inserted}

    # --- 指数技术指标计算 ---

    async def update_index_indicators(self, trade_date: date | None = None) -> dict:
        """计算指定交易日的指数技术指标。

        使用泛化的指标计算引擎，从 index_daily 读取数据，
        计算技术指标后写入 index_technical_daily 表。

        Args:
            trade_date: 目标交易日，None 表示自动检测最新交易日

        Returns:
            计算结果统计：{"trade_date": "YYYY-MM-DD", "total": N, "success": M, "failed": F}
        """
        from app.data.indicator import compute_incremental_generic
        from app.models.index import IndexDaily, IndexTechnicalDaily

        logger.info("[update_index_indicators] 开始计算指数技术指标")

        result = await compute_incremental_generic(
            session_factory=self._session_factory,
            source_table=IndexDaily,
            target_table=IndexTechnicalDaily,
            target_date=trade_date,
        )

        logger.info(
            "[update_index_indicators] 完成：日期 %s，成功 %d 个，失败 %d 个",
            result.get("trade_date"),
            result.get("success", 0),
            result.get("failed", 0),
        )

        return result

    # --- 板块技术指标计算 ---

    async def update_concept_indicators(self, trade_date: date | None = None) -> dict:
        """计算指定交易日的板块技术指标。

        使用泛化的指标计算引擎，从 concept_daily 读取数据，
        计算技术指标后写入 concept_technical_daily 表。

        Args:
            trade_date: 目标交易日，None 表示自动检测最新交易日

        Returns:
            计算结果统计：{"trade_date": "YYYY-MM-DD", "total": N, "success": M, "failed": F}
        """
        from app.data.indicator import compute_incremental_generic
        from app.models.concept import ConceptDaily, ConceptTechnicalDaily

        logger.info("[update_concept_indicators] 开始计算板块技术指标")

        result = await compute_incremental_generic(
            session_factory=self._session_factory,
            source_table=ConceptDaily,
            target_table=ConceptTechnicalDaily,
            target_date=trade_date,
        )

        logger.info(
            "[update_concept_indicators] 完成：日期 %s，成功 %d 个，失败 %d 个",
            result.get("trade_date"),
            result.get("success", 0),
            result.get("failed", 0),
        )

        return result

    # ===================================================================
    # P5 扩展数据同步
    # ===================================================================

    # --- P5 日频 raw 同步 ---

    async def sync_raw_suspend_d(self, trade_date: date) -> dict:
        """按日期获取停复牌信息写入 raw 表（盘后增量模式）。

        suspend_d 接口支持 trade_date 参数，可按日期查询全市场停复牌数据。
        """
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_suspend_d(trade_date=td_str)
        counts = {"suspend_d": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["suspend_d"] = await self._upsert_raw(
                    session, RawTushareSuspendD.__table__, raw_data
                )
                await session.commit()
        logger.info("[sync_raw_suspend_d] %s: %d 条", td_str, counts["suspend_d"])
        return counts

    async def sync_raw_limit_list_d(self, trade_date: date) -> dict:
        """按日期获取涨跌停统计写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_limit_list_d(trade_date=td_str)
        counts = {"limit_list_d": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["limit_list_d"] = await self._upsert_raw(
                    session, RawTushareLimitListD.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_limit_list_d] %s: %d", trade_date, counts["limit_list_d"])
        return counts

    async def sync_raw_margin(self, trade_date: date) -> dict:
        """按日期获取融资融券汇总写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_margin(trade_date=td_str)
        counts = {"margin": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["margin"] = await self._upsert_raw(
                    session, RawTushareMargin.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_margin] %s: %d", trade_date, counts["margin"])
        return counts

    async def sync_raw_margin_detail(self, trade_date: date) -> dict:
        """按日期获取融资融券明细写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_margin_detail(trade_date=td_str)
        counts = {"margin_detail": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["margin_detail"] = await self._upsert_raw(
                    session, RawTushareMarginDetail.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_margin_detail] %s: %d", trade_date, counts["margin_detail"])
        return counts

    async def sync_raw_block_trade(self, trade_date: date) -> dict:
        """按日期获取大宗交易写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_block_trade(trade_date=td_str)
        counts = {"block_trade": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["block_trade"] = await self._upsert_raw(
                    session, RawTushareBlockTrade.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_block_trade] %s: %d", trade_date, counts["block_trade"])
        return counts

    async def sync_raw_daily_share(self, trade_date: date) -> dict:
        """按日期获取每日股本写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_daily_share(trade_date=td_str)
        counts = {"daily_share": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["daily_share"] = await self._upsert_raw(
                    session, RawTushareDailyShare.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_daily_share] %s: %d", trade_date, counts["daily_share"])
        return counts

    async def sync_raw_stk_factor(self, trade_date: date) -> dict:
        """按日期获取技术因子写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_stk_factor(trade_date=td_str)
        counts = {"stk_factor": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_factor"] = await self._upsert_raw(
                    session, RawTushareStkFactor.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_factor] %s: %d", trade_date, counts["stk_factor"])
        return counts

    async def sync_raw_stk_factor_pro(self, trade_date: date) -> dict:
        """按日期获取技术因子Pro写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_stk_factor_pro(trade_date=td_str)
        counts = {"stk_factor_pro": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_factor_pro"] = await self._upsert_raw(
                    session, RawTushareStkFactorPro.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_factor_pro] %s: %d", trade_date, counts["stk_factor_pro"])
        return counts

    async def sync_raw_hm_board(self, trade_date: date) -> dict:
        """按日期获取热门板块写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_hm_board(trade_date=td_str)
        counts = {"hm_board": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["hm_board"] = await self._upsert_raw(
                    session, RawTushareHmBoard.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_hm_board] %s: %d", trade_date, counts["hm_board"])
        return counts

    async def sync_raw_hm_list(self, trade_date: date) -> dict:
        """按日期获取热门股票写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_hm_list(trade_date=td_str)
        counts = {"hm_list": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["hm_list"] = await self._upsert_raw(
                    session, RawTushareHmList.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_hm_list] %s: %d", trade_date, counts["hm_list"])
        return counts

    async def sync_raw_ths_hot(self, trade_date: date) -> dict:
        """按日期获取同花顺热股写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_ths_hot(trade_date=td_str)
        counts = {"ths_hot": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["ths_hot"] = await self._upsert_raw(
                    session, RawTushareThsHot.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_ths_hot] %s: %d", trade_date, counts["ths_hot"])
        return counts

    async def sync_raw_dc_hot(self, trade_date: date) -> dict:
        """按日期获取东财热股写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_dc_hot(trade_date=td_str)
        counts = {"dc_hot": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["dc_hot"] = await self._upsert_raw(
                    session, RawTushareDcHot.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_dc_hot] %s: %d", trade_date, counts["dc_hot"])
        return counts

    async def sync_raw_ths_limit(self, trade_date: date) -> dict:
        """按日期获取同花顺涨跌停写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_ths_limit(trade_date=td_str)
        counts = {"ths_limit": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["ths_limit"] = await self._upsert_raw(
                    session, RawTushareThsLimit.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_ths_limit] %s: %d", trade_date, counts["ths_limit"])
        return counts

    # --- P5 周频/月频 raw 同步 ---

    async def sync_raw_weekly(self, trade_date: date) -> dict:
        """按日期获取周线行情写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_weekly(trade_date=td_str)
        counts = {"weekly": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["weekly"] = await self._upsert_raw(
                    session, RawTushareWeekly.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_weekly] %s: %d", trade_date, counts["weekly"])
        return counts

    async def sync_raw_monthly(self, trade_date: date) -> dict:
        """按日期获取月线行情写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_monthly(trade_date=td_str)
        counts = {"monthly": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["monthly"] = await self._upsert_raw(
                    session, RawTushareMonthly.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_monthly] %s: %d", trade_date, counts["monthly"])
        return counts

    # --- P5 静态/低频 raw 同步 ---

    async def sync_raw_stock_company(self) -> dict:
        """获取上市公司基本信息（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        # 分交易所获取全量数据
        counts = {"stock_company": 0}
        async with self._session_factory() as session:
            for exchange in ("SSE", "SZSE"):
                raw_data = await client.fetch_raw_stock_company(exchange=exchange)
                if raw_data:
                    counts["stock_company"] += await self._upsert_raw(
                        session, RawTushareStockCompany.__table__, raw_data
                    )
            await session.commit()
        logger.debug("[sync_raw_stock_company] total=%d", counts["stock_company"])
        return counts

    async def sync_raw_margin_target(self) -> dict:
        """获取融资融券标的（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_margin_target()
        counts = {"margin_target": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["margin_target"] = await self._upsert_raw(
                    session, RawTushareMarginTarget.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_margin_target] total=%d", counts["margin_target"])
        return counts

    # --- P5 季度 raw 同步 ---

    async def sync_raw_top10_holders(self, trade_date: date) -> dict:
        """按日期获取前十大股东写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_top10_holders(ann_date=td_str)
        counts = {"top10_holders": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["top10_holders"] = await self._upsert_raw(
                    session, RawTushareTop10Holders.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_top10_holders] %s: %d", trade_date, counts["top10_holders"])
        return counts

    async def sync_raw_top10_floatholders(self, trade_date: date) -> dict:
        """按日期获取前十大流通股东写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_top10_floatholders(ann_date=td_str)
        counts = {"top10_floatholders": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["top10_floatholders"] = await self._upsert_raw(
                    session, RawTushareTop10Floatholders.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_top10_floatholders] %s: %d", trade_date, counts["top10_floatholders"])
        return counts

    async def sync_raw_stk_holdernumber(self, trade_date: date) -> dict:
        """按日期获取股东户数写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_stk_holdernumber(enddate=td_str)
        counts = {"stk_holdernumber": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_holdernumber"] = await self._upsert_raw(
                    session, RawTushareStkHoldernumber.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_holdernumber] %s: %d", trade_date, counts["stk_holdernumber"])
        return counts

    async def sync_raw_stk_holdertrade(self, trade_date: date) -> dict:
        """按日期获取股东增减持写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_stk_holdertrade(ann_date=td_str)
        counts = {"stk_holdertrade": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_holdertrade"] = await self._upsert_raw(
                    session, RawTushareStkHoldertrade.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_holdertrade] %s: %d", trade_date, counts["stk_holdertrade"])
        return counts

    # --- P5 补充数据 raw 同步（28 张表） ---

    # 1. 基础补充表（5 张）

    async def sync_raw_namechange(self) -> dict:
        """获取股票曾用名（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_namechange()
        counts = {"namechange": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["namechange"] = await self._upsert_raw(
                    session, RawTushareNamechange.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_namechange] total=%d", counts["namechange"])
        return counts

    async def sync_raw_stk_managers(self) -> dict:
        """获取上市公司管理层（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_stk_managers()
        counts = {"stk_managers": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_managers"] = await self._upsert_raw(
                    session, RawTushareStkManagers.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_managers] total=%d", counts["stk_managers"])
        return counts

    async def sync_raw_stk_rewards(self) -> dict:
        """获取管理层薪酬和持股（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_stk_rewards()
        counts = {"stk_rewards": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_rewards"] = await self._upsert_raw(
                    session, RawTushareStkRewards.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_rewards] total=%d", counts["stk_rewards"])
        return counts

    async def sync_raw_new_share(self) -> dict:
        """获取 IPO 新股列表（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_new_share()
        counts = {"new_share": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["new_share"] = await self._upsert_raw(
                    session, RawTushareNewShare.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_new_share] total=%d", counts["new_share"])
        return counts

    async def sync_raw_stk_list_his(self) -> dict:
        """获取股票上市历史（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_stk_list_his()
        counts = {"stk_list_his": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_list_his"] = await self._upsert_raw(
                    session, RawTushareStkListHis.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_list_his] total=%d", counts["stk_list_his"])
        return counts

    # 2. 行情补充表（2 张）

    async def sync_raw_hsgt_top10(self, trade_date: date) -> dict:
        """按日期获取沪深港通十大成交股写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_hsgt_top10(trade_date=td_str)
        counts = {"hsgt_top10": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["hsgt_top10"] = await self._upsert_raw(
                    session, RawTushareHsgtTop10.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_hsgt_top10] %s: %d", trade_date, counts["hsgt_top10"])
        return counts

    async def sync_raw_ggt_daily(self, trade_date: date) -> dict:
        """按日期获取港股通每日成交统计写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_ggt_daily(trade_date=td_str)
        counts = {"ggt_daily": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["ggt_daily"] = await self._upsert_raw(
                    session, RawTushareGgtDaily.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_ggt_daily] %s: %d", trade_date, counts["ggt_daily"])
        return counts

    # 3. 市场参考表（4 张）

    async def sync_raw_pledge_stat(self) -> dict:
        """获取股权质押统计（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_pledge_stat()
        counts = {"pledge_stat": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["pledge_stat"] = await self._upsert_raw(
                    session, RawTusharePledgeStat.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_pledge_stat] total=%d", counts["pledge_stat"])
        return counts

    async def sync_raw_pledge_detail(self) -> dict:
        """获取股权质押明细（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_pledge_detail()
        counts = {"pledge_detail": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["pledge_detail"] = await self._upsert_raw(
                    session, RawTusharePledgeDetail.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_pledge_detail] total=%d", counts["pledge_detail"])
        return counts

    async def sync_raw_repurchase(self) -> dict:
        """获取股票回购（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_repurchase()
        counts = {"repurchase": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["repurchase"] = await self._upsert_raw(
                    session, RawTushareRepurchase.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_repurchase] total=%d", counts["repurchase"])
        return counts

    async def sync_raw_share_float(self, trade_date: date) -> dict:
        """按日期获取限售股解禁写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_share_float(ann_date=td_str)
        counts = {"share_float": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["share_float"] = await self._upsert_raw(
                    session, RawTushareShareFloat.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_share_float] %s: %d", trade_date, counts["share_float"])
        return counts

    # 4. 特色数据表（7 张）

    async def sync_raw_report_rc(self, trade_date: date) -> dict:
        """按日期获取券商月度金股写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_report_rc(date=td_str)
        counts = {"report_rc": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["report_rc"] = await self._upsert_raw(
                    session, RawTushareReportRc.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_report_rc] %s: %d", trade_date, counts["report_rc"])
        return counts

    async def sync_raw_cyq_perf(self, trade_date: date) -> dict:
        """按日期获取筹码分布写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_cyq_perf(trade_date=td_str)
        counts = {"cyq_perf": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["cyq_perf"] = await self._upsert_raw(
                    session, RawTushareCyqPerf.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_cyq_perf] %s: %d", trade_date, counts["cyq_perf"])
        return counts

    async def sync_raw_cyq_chips(self, trade_date: date) -> dict:
        """按日期获取筹码集中度写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_cyq_chips(trade_date=td_str)
        counts = {"cyq_chips": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["cyq_chips"] = await self._upsert_raw(
                    session, RawTushareCyqChips.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_cyq_chips] %s: %d", trade_date, counts["cyq_chips"])
        return counts

    async def sync_raw_ccass_hold(self, trade_date: date) -> dict:
        """按日期获取港股通持股汇总写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_ccass_hold(trade_date=td_str)
        counts = {"ccass_hold": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["ccass_hold"] = await self._upsert_raw(
                    session, RawTushareCcassHold.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_ccass_hold] %s: %d", trade_date, counts["ccass_hold"])
        return counts

    async def sync_raw_ccass_hold_detail(self, trade_date: date) -> dict:
        """按日期获取港股通持股明细写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_ccass_hold_detail(trade_date=td_str)
        counts = {"ccass_hold_detail": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["ccass_hold_detail"] = await self._upsert_raw(
                    session, RawTushareCcassHoldDetail.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_ccass_hold_detail] %s: %d", trade_date, counts["ccass_hold_detail"])
        return counts

    async def sync_raw_hk_hold(self, trade_date: date) -> dict:
        """按日期获取沪深港通持股明细写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_hk_hold(trade_date=td_str)
        counts = {"hk_hold": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["hk_hold"] = await self._upsert_raw(
                    session, RawTushareHkHold.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_hk_hold] %s: %d", trade_date, counts["hk_hold"])
        return counts

    async def sync_raw_stk_surv(self) -> dict:
        """获取机构调研（全量）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        raw_data = await client.fetch_raw_stk_surv()
        counts = {"stk_surv": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_surv"] = await self._upsert_raw(
                    session, RawTushareStkSurv.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_surv] total=%d", counts["stk_surv"])
        return counts

    # 5. 两融补充表（1 张）

    async def sync_raw_slb_len(self, trade_date: date) -> dict:
        """按日期获取转融通借入写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_slb_len(trade_date=td_str)
        counts = {"slb_len": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["slb_len"] = await self._upsert_raw(
                    session, RawTushareSlbLen.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_slb_len] %s: %d", trade_date, counts["slb_len"])
        return counts

    # 6. 打板专题表（9 张）

    async def sync_raw_limit_step(self, trade_date: date) -> dict:
        """按日期获取涨跌停阶梯写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_limit_step(trade_date=td_str)
        counts = {"limit_step": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["limit_step"] = await self._upsert_raw(
                    session, RawTushareLimitStep.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_limit_step] %s: %d", trade_date, counts["limit_step"])
        return counts

    async def sync_raw_hm_detail(self, trade_date: date) -> dict:
        """按日期获取热门股票明细写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_hm_detail(trade_date=td_str)
        counts = {"hm_detail": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["hm_detail"] = await self._upsert_raw(
                    session, RawTushareHmDetail.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_hm_detail] %s: %d", trade_date, counts["hm_detail"])
        return counts

    async def sync_raw_stk_auction(self, trade_date: date) -> dict:
        """按日期获取集合竞价写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_stk_auction(trade_date=td_str)
        counts = {"stk_auction": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_auction"] = await self._upsert_raw(
                    session, RawTushareStkAuction.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_auction] %s: %d", trade_date, counts["stk_auction"])
        return counts

    async def sync_raw_stk_auction_o(self, trade_date: date) -> dict:
        """按日期获取集合竞价（开盘）写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_stk_auction_o(trade_date=td_str)
        counts = {"stk_auction_o": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["stk_auction_o"] = await self._upsert_raw(
                    session, RawTushareStkAuctionO.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_stk_auction_o] %s: %d", trade_date, counts["stk_auction_o"])
        return counts

    async def sync_raw_kpl_list(self, trade_date: date) -> dict:
        """按日期获取开盘啦涨跌停写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_kpl_list(trade_date=td_str)
        counts = {"kpl_list": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["kpl_list"] = await self._upsert_raw(
                    session, RawTushareKplList.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_kpl_list] %s: %d", trade_date, counts["kpl_list"])
        return counts

    async def sync_raw_kpl_concept(self, trade_date: date) -> dict:
        """按日期获取开盘啦概念写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        td_str = trade_date.strftime("%Y%m%d")
        raw_data = await client.fetch_raw_kpl_concept(trade_date=td_str)
        counts = {"kpl_concept": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["kpl_concept"] = await self._upsert_raw(
                    session, RawTushareKplConcept.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_kpl_concept] %s: %d", trade_date, counts["kpl_concept"])
        return counts

    async def sync_raw_broker_recommend(self, trade_date: date) -> dict:
        """按月份获取券商推荐写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        month_str = trade_date.strftime("%Y%m")
        raw_data = await client.fetch_raw_broker_recommend(month=month_str)
        counts = {"broker_recommend": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["broker_recommend"] = await self._upsert_raw(
                    session, RawTushareBrokerRecommend.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_broker_recommend] %s: %d", trade_date, counts["broker_recommend"])
        return counts

    async def sync_raw_ggt_monthly(self, trade_date: date) -> dict:
        """按月份获取港股通月度统计写入 raw 表。"""
        from app.data.tushare import TushareClient
        client: TushareClient = self._primary_client  # type: ignore[assignment]
        month_str = trade_date.strftime("%Y%m")
        raw_data = await client.fetch_raw_ggt_monthly(month=month_str)
        counts = {"ggt_monthly": 0}
        async with self._session_factory() as session:
            if raw_data:
                counts["ggt_monthly"] = await self._upsert_raw(
                    session, RawTushareGgtMonthly.__table__, raw_data
                )
            await session.commit()
        logger.debug("[sync_raw_ggt_monthly] %s: %d", trade_date, counts["ggt_monthly"])
        return counts

    # --- P5 ETL 方法 ---

    async def etl_suspend(self, trade_date: date) -> dict:
        """从 raw 表读取停复牌数据，清洗后写入 suspend_info 业务表。

        Args:
            trade_date: 交易日期

        Returns:
            {"suspend_info": int}
        """
        td_str = trade_date.strftime("%Y%m%d")

        async with self._session_factory() as session:
            result = await session.execute(
                select(RawTushareSuspendD).where(
                    RawTushareSuspendD.suspend_date == td_str
                )
            )
            raw_rows = [
                {c.key: getattr(r, c.key) for c in RawTushareSuspendD.__table__.columns if c.key != "fetched_at"}
                for r in result.scalars().all()
            ]

        cleaned = transform_tushare_suspend_d(raw_rows)
        counts = {"suspend_info": 0}

        async with self._session_factory() as session:
            if cleaned:
                counts["suspend_info"] = await batch_insert(
                    session, SuspendInfo.__table__, cleaned
                )

        logger.debug("[etl_suspend] %s: %d", trade_date, counts["suspend_info"])
        return counts

    async def etl_limit_list(self, trade_date: date) -> dict:
        """从 raw 表读取涨跌停统计数据，清洗后写入 limit_list_daily 业务表。

        Args:
            trade_date: 交易日期

        Returns:
            {"limit_list_daily": int}
        """
        td_str = trade_date.strftime("%Y%m%d")

        async with self._session_factory() as session:
            result = await session.execute(
                select(RawTushareLimitListD).where(
                    RawTushareLimitListD.trade_date == td_str
                )
            )
            raw_rows = [
                {c.key: getattr(r, c.key) for c in RawTushareLimitListD.__table__.columns if c.key != "fetched_at"}
                for r in result.scalars().all()
            ]

        cleaned = transform_tushare_limit_list_d(raw_rows)
        counts = {"limit_list_daily": 0}

        async with self._session_factory() as session:
            if cleaned:
                counts["limit_list_daily"] = await batch_insert(
                    session, LimitListDaily.__table__, cleaned
                )

        logger.debug("[etl_limit_list] %s: %d", trade_date, counts["limit_list_daily"])
        return counts

    # --- P5 聚合入口 ---

    async def sync_p5_core(self, trade_date: date) -> dict:
        """P5 核心数据聚合同步：按频率分组调用所有 P5 同步和 ETL 方法。

        - 日频（13+15 张表 + 2 个 ETL）：每个交易日执行
        - 周频（weekly）：仅周五执行
        - 月频（monthly + ggt_monthly）：仅月末最后一个交易日执行
        - 季度（股东数据 4 张表）：每个交易日尝试获取（接口按公告日期返回）
        - 静态（stock_company, margin_target + 11 张补充表）：每季度首个交易日执行

        Args:
            trade_date: 交易日期

        Returns:
            各步骤结果汇总
        """
        import calendar
        import time
        import traceback

        start = time.monotonic()
        results: dict = {}

        # --- 日频 raw 同步（13 张核心表） ---
        daily_methods = [
            ("suspend_d", self.sync_raw_suspend_d),
            ("limit_list_d", self.sync_raw_limit_list_d),
            ("margin", self.sync_raw_margin),
            ("margin_detail", self.sync_raw_margin_detail),
            ("block_trade", self.sync_raw_block_trade),
            ("daily_share", self.sync_raw_daily_share),
            ("stk_factor", self.sync_raw_stk_factor),
            ("stk_factor_pro", self.sync_raw_stk_factor_pro),
            ("hm_board", self.sync_raw_hm_board),
            ("hm_list", self.sync_raw_hm_list),
            ("ths_hot", self.sync_raw_ths_hot),
            ("dc_hot", self.sync_raw_dc_hot),
            ("ths_limit", self.sync_raw_ths_limit),
        ]
        for name, method in daily_methods:
            try:
                r = await method(trade_date)
                results[name] = r
            except Exception:
                logger.warning("[sync_p5_core] %s 失败\n%s", name, traceback.format_exc())
                results[name] = {"error": True}

        # --- 日频补充表同步（15 张） ---
        daily_ext_methods: list[tuple[str, object]] = [
            ("hsgt_top10", self.sync_raw_hsgt_top10),
            ("ggt_daily", self.sync_raw_ggt_daily),
            ("ccass_hold", self.sync_raw_ccass_hold),
            ("ccass_hold_detail", self.sync_raw_ccass_hold_detail),
            ("hk_hold", self.sync_raw_hk_hold),
            ("cyq_perf", self.sync_raw_cyq_perf),
            ("cyq_chips", self.sync_raw_cyq_chips),
            ("slb_len", self.sync_raw_slb_len),
            ("limit_step", self.sync_raw_limit_step),
            ("hm_detail", self.sync_raw_hm_detail),
            ("stk_auction", self.sync_raw_stk_auction),
            ("stk_auction_o", self.sync_raw_stk_auction_o),
            ("kpl_list", self.sync_raw_kpl_list),
            ("kpl_concept", self.sync_raw_kpl_concept),
            ("broker_recommend", self.sync_raw_broker_recommend),
        ]
        for name, method in daily_ext_methods:
            try:
                r = await method(trade_date)
                results[name] = r
            except Exception:
                logger.warning("[sync_p5_core] %s 失败\n%s", name, traceback.format_exc())
                results[name] = {"error": True}

        # --- 日频 ETL（停复牌 + 涨跌停） ---
        for name, method in [("etl_suspend", self.etl_suspend), ("etl_limit_list", self.etl_limit_list)]:
            try:
                r = await method(trade_date)
                results[name] = r
            except Exception:
                logger.warning("[sync_p5_core] %s 失败\n%s", name, traceback.format_exc())
                results[name] = {"error": True}

        # --- 周频：仅周五执行 ---
        if trade_date.weekday() == 4:  # 周五
            try:
                r = await self.sync_raw_weekly(trade_date)
                results["weekly"] = r
            except Exception:
                logger.warning("[sync_p5_core] weekly 失败\n%s", traceback.format_exc())
                results["weekly"] = {"error": True}

        # --- 月频：仅月末最后一个交易日执行 ---
        last_day = calendar.monthrange(trade_date.year, trade_date.month)[1]
        if trade_date.day == last_day or (last_day - trade_date.day <= 3 and trade_date.weekday() == 4):
            # 月末当天或月末前最后一个周五（兜底）
            for name, method in [("monthly", self.sync_raw_monthly), ("ggt_monthly", self.sync_raw_ggt_monthly)]:
                try:
                    r = await method(trade_date)
                    results[name] = r
                except Exception:
                    logger.warning("[sync_p5_core] %s 失败\n%s", name, traceback.format_exc())
                    results[name] = {"error": True}

        # --- 季度数据：每个交易日尝试获取（按公告日期） ---
        quarterly_methods = [
            ("top10_holders", self.sync_raw_top10_holders),
            ("top10_floatholders", self.sync_raw_top10_floatholders),
            ("stk_holdernumber", self.sync_raw_stk_holdernumber),
            ("stk_holdertrade", self.sync_raw_stk_holdertrade),
        ]
        for name, method in quarterly_methods:
            try:
                r = await method(trade_date)
                results[name] = r
            except Exception:
                logger.warning("[sync_p5_core] %s 失败\n%s", name, traceback.format_exc())
                results[name] = {"error": True}

        # --- 静态数据：每季度首个交易日执行（1/1, 4/1, 7/1, 10/1 附近） ---
        if trade_date.day <= 3 and trade_date.month in (1, 4, 7, 10):
            # 无参数的静态方法
            static_no_arg = [
                ("stock_company", self.sync_raw_stock_company),
                ("margin_target", self.sync_raw_margin_target),
                ("namechange", self.sync_raw_namechange),
                ("stk_managers", self.sync_raw_stk_managers),
                ("stk_rewards", self.sync_raw_stk_rewards),
                ("new_share", self.sync_raw_new_share),
                ("stk_list_his", self.sync_raw_stk_list_his),
                ("pledge_stat", self.sync_raw_pledge_stat),
                ("pledge_detail", self.sync_raw_pledge_detail),
                ("repurchase", self.sync_raw_repurchase),
                ("stk_surv", self.sync_raw_stk_surv),
            ]
            for name, method in static_no_arg:
                try:
                    r = await method()
                    results[name] = r
                except Exception:
                    logger.warning("[sync_p5_core] %s 失败\n%s", name, traceback.format_exc())
                    results[name] = {"error": True}
            # 需要 trade_date 的低频方法
            static_with_date = [
                ("share_float", self.sync_raw_share_float),
                ("report_rc", self.sync_raw_report_rc),
            ]
            for name, method in static_with_date:
                try:
                    r = await method(trade_date)
                    results[name] = r
                except Exception:
                    logger.warning("[sync_p5_core] %s 失败\n%s", name, traceback.format_exc())
                    results[name] = {"error": True}

        # --- 更新 raw_sync_progress ---
        # 方法名 → raw 表名映射（从 TABLE_GROUP_MAP["p5"] 提取）
        _method_to_raw: dict[str, str] = {}
        for raw_table, method_name, freq, _ in self.TABLE_GROUP_MAP.get("p5", []):
            # method_name 形如 "sync_raw_suspend_d"，去掉 "sync_raw_" 前缀得到 key
            short = method_name.removeprefix("sync_raw_")
            _method_to_raw[short] = raw_table
        for name, result in results.items():
            if isinstance(result, dict) and not result.get("error"):
                raw_table = _method_to_raw.get(name)
                if raw_table:
                    # 取 result 中第一个 int 值作为行数
                    rows = next((v for v in result.values() if isinstance(v, int)), 0)
                    await self._update_raw_sync_progress(raw_table, trade_date, rows)

        elapsed = time.monotonic() - start
        error_count = sum(1 for v in results.values() if isinstance(v, dict) and v.get("error"))
        logger.info(
            "[sync_p5_core] %s 完成：%d 步骤，%d 失败，耗时 %.1fs",
            trade_date, len(results), error_count, elapsed,
        )
        return results

    # ===================================================================
    # 统一同步入口（Task 3.1-3.4）
    # ===================================================================

    # 表组映射：每个条目为 (raw_table_name, sync_method_name, freq, etl_method_name|None)
    # freq: "daily"=按交易日, "static"=无日期参数, "period"=按季度
    TABLE_GROUP_MAP: dict[str, list[tuple[str, str, str, str | None]]] = {
        "p0": [
            ("raw_tushare_daily", "sync_raw_daily", "daily", "etl_daily"),
        ],
        "p1": [
            ("raw_tushare_fina_indicator", "sync_raw_fina", "period", "etl_fina"),
        ],
        "p2": [
            ("raw_tushare_moneyflow", "sync_raw_moneyflow", "daily", None),
            ("raw_tushare_top_list", "sync_raw_top_list", "daily", "etl_moneyflow"),
        ],
        "p3_daily": [
            ("raw_tushare_index_daily", "sync_raw_index_daily", "bulk_daily", None),
            ("raw_tushare_index_weight", "sync_raw_index_weight", "bulk_daily", None),
            ("raw_tushare_index_factor_pro", "sync_raw_index_technical", "bulk_daily", "etl_index"),
        ],
        "p3_static": [
            ("raw_tushare_index_basic", "sync_raw_index_basic", "static", None),
            ("raw_tushare_index_classify", "sync_raw_industry_classify", "static", None),
            ("raw_tushare_index_member_all", "sync_raw_industry_member", "static", "etl_index_static"),
        ],
        "p5": [
            # 日频核心
            ("raw_tushare_suspend_d", "sync_raw_suspend_d", "daily", "etl_suspend"),
            ("raw_tushare_limit_list_d", "sync_raw_limit_list_d", "daily", "etl_limit_list"),
            ("raw_tushare_margin", "sync_raw_margin", "daily", None),
            ("raw_tushare_margin_detail", "sync_raw_margin_detail", "daily", None),
            ("raw_tushare_block_trade", "sync_raw_block_trade", "daily", None),
            # daily_share: Tushare 无此接口名，已禁用
            # ("raw_tushare_daily_share", "sync_raw_daily_share", "daily", None),
            ("raw_tushare_stk_factor", "sync_raw_stk_factor", "daily", None),
            ("raw_tushare_stk_factor_pro", "sync_raw_stk_factor_pro", "daily", None),
            # hm_board: Tushare 无此接口名，已禁用
            # ("raw_tushare_hm_board", "sync_raw_hm_board", "daily", None),
            ("raw_tushare_hm_list", "sync_raw_hm_list", "daily", None),
            ("raw_tushare_ths_hot", "sync_raw_ths_hot", "daily", None),
            ("raw_tushare_dc_hot", "sync_raw_dc_hot", "daily", None),
            # ths_limit: Tushare 无此接口名，已禁用
            # ("raw_tushare_ths_limit", "sync_raw_ths_limit", "daily", None),
            # 日频补充
            ("raw_tushare_hsgt_top10", "sync_raw_hsgt_top10", "daily", None),
            ("raw_tushare_ggt_daily", "sync_raw_ggt_daily", "daily", None),
            ("raw_tushare_ccass_hold", "sync_raw_ccass_hold", "daily", None),
            ("raw_tushare_ccass_hold_detail", "sync_raw_ccass_hold_detail", "daily", None),
            ("raw_tushare_hk_hold", "sync_raw_hk_hold", "daily", None),
            ("raw_tushare_cyq_perf", "sync_raw_cyq_perf", "daily", None),
            # cyq_chips: 需要 ts_code 必填参数，不支持全市场批量查询，已禁用
            # ("raw_tushare_cyq_chips", "sync_raw_cyq_chips", "daily", None),
            ("raw_tushare_slb_len", "sync_raw_slb_len", "daily", None),
            # limit_step: Tushare 接口权限不足，已禁用
            # ("raw_tushare_limit_step", "sync_raw_limit_step", "daily", None),
            # hm_detail: Tushare 接口频率限制（每小时 2 次），已禁用
            # ("raw_tushare_hm_detail", "sync_raw_hm_detail", "daily", None),
            ("raw_tushare_stk_auction", "sync_raw_stk_auction", "daily", None),
            # stk_auction_o: Tushare 接口权限不足，已禁用
            # ("raw_tushare_stk_auction_o", "sync_raw_stk_auction_o", "daily", None),
            ("raw_tushare_kpl_list", "sync_raw_kpl_list", "daily", None),
            ("raw_tushare_kpl_concept", "sync_raw_kpl_concept", "daily", None),
            ("raw_tushare_broker_recommend", "sync_raw_broker_recommend", "daily", None),
            # 周频/月频
            ("raw_tushare_weekly", "sync_raw_weekly", "daily", None),
            ("raw_tushare_monthly", "sync_raw_monthly", "daily", None),
            ("raw_tushare_ggt_monthly", "sync_raw_ggt_monthly", "daily", None),
            # 季度
            ("raw_tushare_top10_holders", "sync_raw_top10_holders", "daily", None),
            ("raw_tushare_top10_floatholders", "sync_raw_top10_floatholders", "daily", None),
            ("raw_tushare_stk_holdernumber", "sync_raw_stk_holdernumber", "daily", None),
            ("raw_tushare_stk_holdertrade", "sync_raw_stk_holdertrade", "daily", None),
            # 静态
            ("raw_tushare_stock_company", "sync_raw_stock_company", "static", None),
            ("raw_tushare_margin_target", "sync_raw_margin_target", "static", None),
            ("raw_tushare_namechange", "sync_raw_namechange", "static", None),
            ("raw_tushare_stk_managers", "sync_raw_stk_managers", "static", None),
            # stk_rewards: 需要 ts_code 必填参数，不支持全市场批量查询，已禁用
            # ("raw_tushare_stk_rewards", "sync_raw_stk_rewards", "static", None),
            ("raw_tushare_new_share", "sync_raw_new_share", "static", None),
            # stk_list_his: Tushare 无此接口名，已禁用
            # ("raw_tushare_stk_list_his", "sync_raw_stk_list_his", "static", None),
            ("raw_tushare_pledge_stat", "sync_raw_pledge_stat", "static", None),
            # pledge_detail: 需要 ts_code 必填参数，不支持全市场批量查询，已禁用
            # ("raw_tushare_pledge_detail", "sync_raw_pledge_detail", "static", None),
            ("raw_tushare_repurchase", "sync_raw_repurchase", "static", None),
            ("raw_tushare_stk_surv", "sync_raw_stk_surv", "static", None),
            ("raw_tushare_share_float", "sync_raw_share_float", "daily", None),
            ("raw_tushare_report_rc", "sync_raw_report_rc", "daily", None),
        ],
        "p4": [
            # P4 板块数据通过 sync_concept_* 方法同步，不在此映射中
            # 因为板块同步逻辑较特殊（需要遍历板块代码），由盘后链路步骤 3.7 单独处理
        ],
    }

    @classmethod
    def _resolve_table_groups(cls, table_group: str | list[str]) -> list[tuple[str, str, str, str | None]]:
        """解析 table_group 参数，返回合并后的表列表。"""
        if table_group == "all":
            groups = ["p0", "p1", "p2", "p3_daily", "p3_static", "p4", "p5"]
        elif isinstance(table_group, str):
            # 单个字符串：p3 展开为 p3_daily + p3_static
            if table_group == "p3":
                groups = ["p3_daily", "p3_static"]
            else:
                groups = [table_group]
        else:
            # 列表：逐个展开，p3 → p3_daily + p3_static
            groups = []
            for g in table_group:
                if g == "p3":
                    groups.extend(["p3_daily", "p3_static"])
                else:
                    groups.append(g)

        result = []
        for g in groups:
            entries = cls.TABLE_GROUP_MAP.get(g, [])
            result.extend(entries)
        return result

    async def sync_raw_tables(
        self,
        table_group: str | list[str],
        start_date: date,
        end_date: date,
        mode: str = "incremental",
    ) -> dict:
        """统一同步入口：按表组和模式同步 raw 表并执行 ETL。

        Args:
            table_group: "p0"/"p1"/"p2"/"p3"/"p4"/"p5"/"all" 或列表
            start_date: 起始日期（full 模式使用）
            end_date: 结束日期（通常为目标交易日）
            mode: "full"=全量, "incremental"=仅 end_date, "gap_fill"=基于进度补缺口

        Returns:
            {table_name: {rows: int, error: str|None}, ...}
        """
        import time
        import traceback

        chain_start = time.monotonic()
        entries = self._resolve_table_groups(table_group)
        if not entries:
            logger.warning("[sync_raw_tables] 表组 %s 无对应条目", table_group)
            return

        # 获取交易日列表（用于 full/gap_fill 模式）
        trading_dates: list[date] = []
        if mode in ("full", "gap_fill"):
            trading_dates = await self.get_trade_calendar(start_date, end_date)

        # 获取 raw_sync_progress（用于 gap_fill 模式）
        progress_map: dict[str, date | None] = {}
        if mode == "gap_fill":
            async with self._session_factory() as session:
                from app.models.market import RawSyncProgress
                result = await session.execute(select(RawSyncProgress))
                for row in result.scalars().all():
                    progress_map[row.table_name] = row.last_sync_date

        results: dict = {}
        total_entries = len(entries)

        for entry_idx, (raw_table, sync_method_name, freq, etl_method_name) in enumerate(entries, 1):
            sync_method = getattr(self, sync_method_name, None)
            if sync_method is None:
                logger.warning("[sync_raw_tables] 方法 %s 不存在，跳过", sync_method_name)
                continue

            # 确定要同步的日期列表
            if freq == "static":
                dates_to_sync = [None]
            elif freq == "period":
                dates_to_sync = [None]
            elif freq == "bulk_daily":
                dates_to_sync = [end_date]  # 占位，实际在下面特殊处理
            elif mode == "incremental":
                dates_to_sync = [end_date]
            elif mode == "full":
                dates_to_sync = trading_dates
            elif mode == "gap_fill":
                last_sync = progress_map.get(raw_table)
                if last_sync and last_sync >= end_date:
                    logger.debug("[sync_raw_tables] %s 已追平，跳过", raw_table)
                    continue
                gap_start = (last_sync + timedelta(days=1)) if last_sync else start_date
                dates_to_sync = [d for d in trading_dates if d >= gap_start]
            else:
                dates_to_sync = [end_date]

            table_start = time.monotonic()
            total_rows = 0
            error_msg = None
            total_dates = len(dates_to_sync)

            for date_idx, td in enumerate(dates_to_sync, 1):
                try:
                    if freq == "static":
                        r = await sync_method()
                    elif freq == "period":
                        if td is not None:
                            period_str = td.strftime("%Y%m%d")
                            r = await sync_method(period_str)
                        else:
                            r = {}
                    elif freq == "bulk_daily":
                        if mode in ("full", "gap_fill") and start_date and end_date:
                            r = await sync_method(start_date, end_date=end_date)
                        else:
                            r = await sync_method(td)
                    else:
                        r = await sync_method(td)
                    # 累加行数
                    rows = 0
                    if isinstance(r, dict):
                        rows = sum(v for v in r.values() if isinstance(v, int))
                        total_rows += rows
                    # 日频表且多日：每个日期 1 条日志
                    if freq == "daily" and total_dates > 1:
                        logger.info(
                            "[sync] %s [表%d/%d] [%d/%d] %s ✓ %d行",
                            raw_table, entry_idx, total_entries,
                            date_idx, total_dates, td, rows,
                        )
                except Exception:
                    error_msg = traceback.format_exc()[-200:]
                    if freq == "daily" and total_dates > 1:
                        logger.warning(
                            "[sync] %s [表%d/%d] [%d/%d] %s ✗ %s",
                            raw_table, entry_idx, total_entries,
                            date_idx, total_dates, td, error_msg[:80],
                        )
                    else:
                        logger.warning(
                            "[sync_raw_tables] %s 在 %s 失败: %s",
                            raw_table, td, error_msg,
                        )

            # 执行对应的 ETL
            if etl_method_name and error_msg is None:
                etl_method = getattr(self, etl_method_name, None)
                if etl_method:
                    # 静态表 ETL：无参数直接调用
                    if freq == "static":
                        try:
                            await etl_method()
                            logger.info(
                                "[sync] ETL %s [表%d/%d] 静态 ✓",
                                etl_method_name, entry_idx, total_entries,
                            )
                        except Exception:
                            logger.warning(
                                "[sync] ETL %s [表%d/%d] 静态 ✗ %s",
                                etl_method_name, entry_idx, total_entries,
                                traceback.format_exc()[-200:],
                            )
                    else:
                        if mode == "incremental":
                            # 增量模式：仅对最新日期执行 ETL
                            etl_dates = [end_date]
                        elif mode in ("full", "gap_fill") and freq in ("daily", "bulk_daily"):
                            # 全量/补缺模式：逐日执行 ETL
                            etl_dates = trading_dates if trading_dates else [end_date]
                        elif freq == "period":
                            etl_dates = [end_date]
                        else:
                            etl_dates = [end_date]

                        etl_ok = 0
                        etl_fail = 0
                        for etl_idx, etl_td in enumerate(etl_dates, 1):
                            try:
                                if freq == "period":
                                    await etl_method(etl_td.strftime("%Y%m%d"))
                                else:
                                    await etl_method(etl_td)
                                etl_ok += 1
                                if len(etl_dates) > 1 and etl_idx % 100 == 0:
                                    logger.info(
                                        "[sync] ETL %s [%d/%d] %s ✓",
                                        etl_method_name, etl_idx, len(etl_dates), etl_td,
                                    )
                            except Exception:
                                etl_fail += 1
                                logger.warning(
                                    "[sync] ETL %s [表%d/%d] %s ✗ %s",
                                    etl_method_name, entry_idx, total_entries,
                                    etl_td, traceback.format_exc()[-200:],
                                )
                        if len(etl_dates) == 1:
                            if etl_ok:
                                logger.info(
                                    "[sync] ETL %s [表%d/%d] %s ✓",
                                    etl_method_name, entry_idx, total_entries, end_date,
                                )
                        else:
                            logger.info(
                                "[sync] ETL %s [表%d/%d] 完成：%d 成功，%d 失败",
                                etl_method_name, entry_idx, total_entries, etl_ok, etl_fail,
                            )

            results[raw_table] = {"rows": total_rows, "error": error_msg}

            # 表完成汇总
            table_elapsed = time.monotonic() - table_start
            if freq == "static":
                logger.info(
                    "[sync] %s [表%d/%d] 静态 ✓ %d行，耗时%.1fs",
                    raw_table, entry_idx, total_entries, total_rows, table_elapsed,
                )
            elif freq == "bulk_daily" and mode in ("full", "gap_fill"):
                logger.info(
                    "[sync] %s [表%d/%d] 批量 %s~%s ✓ %d行，耗时%.1fs",
                    raw_table, entry_idx, total_entries,
                    start_date, end_date, total_rows, table_elapsed,
                )
            elif total_dates > 1:
                logger.info(
                    "[sync] %s [表%d/%d] 完成：%d日，共%d行，耗时%.1fs",
                    raw_table, entry_idx, total_entries,
                    total_dates, total_rows, table_elapsed,
                )
            else:
                logger.info(
                    "[sync] %s [表%d/%d] %s ✓ %d行，耗时%.1fs",
                    raw_table, entry_idx, total_entries,
                    end_date, total_rows, table_elapsed,
                )

            # 更新 raw_sync_progress（Task 3.4）
            if error_msg is None and freq != "static":
                await self._update_raw_sync_progress(
                    raw_table, end_date, total_rows
                )

        elapsed = time.monotonic() - chain_start
        ok_count = sum(1 for v in results.values() if v.get("error") is None)
        fail_count = len(results) - ok_count
        logger.info(
            "[sync_raw_tables] group=%s mode=%s 完成：%d 成功，%d 失败，耗时 %.1fs",
            table_group, mode, ok_count, fail_count, elapsed,
        )
        return results

    async def _update_raw_sync_progress(
        self, table_name: str, sync_date: date, rows: int
    ) -> None:
        """更新 raw_sync_progress 表中某张 raw 表的同步进度。"""
        from app.models.market import RawSyncProgress

        async with self._session_factory() as session:
            stmt = pg_insert(RawSyncProgress.__table__).values(
                table_name=table_name,
                last_sync_date=sync_date,
                last_sync_rows=rows,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["table_name"],
                set_={
                    "last_sync_date": stmt.excluded.last_sync_date,
                    "last_sync_rows": stmt.excluded.last_sync_rows,
                },
            )
            await session.execute(stmt)
            await session.commit()

    async def _get_raw_sync_summary(self, target_date: date) -> dict:
        """获取 raw 表同步进度摘要。

        Returns:
            {total_tables, up_to_date, stale, never_synced}
        """
        from app.models.market import RawSyncProgress

        # 收集所有已注册的 raw 表名
        all_tables = set()
        for entries in self.TABLE_GROUP_MAP.values():
            for raw_table, _, _, _ in entries:
                all_tables.add(raw_table)

        async with self._session_factory() as session:
            result = await session.execute(select(RawSyncProgress))
            progress_rows = {r.table_name: r.last_sync_date for r in result.scalars().all()}

        up_to_date = 0
        stale = 0
        never_synced = 0
        for table in all_tables:
            last_date = progress_rows.get(table)
            if last_date is None:
                never_synced += 1
            elif last_date >= target_date:
                up_to_date += 1
            else:
                stale += 1

        return {
            "total_tables": len(all_tables),
            "up_to_date": up_to_date,
            "stale": stale,
            "never_synced": never_synced,
        }
