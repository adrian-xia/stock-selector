"""综合跨表一致性校验测试。

测试范围：
- 时间连续性校验
- stock_daily 与 index_daily 交易日一致性
- stock_daily 与 money_flow 交易日一致性
- stocks 表与 stock_daily ts_code 一致性
- index_daily 与 index_basic 指数代码一致性
- concept_daily 与 concept_index 板块代码一致性
- raw_tushare_daily 三表 JOIN 完整性
- 全链路数据新鲜度校验
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.raw import (
    RawTushareDaily,
    RawTushareAdjFactor,
    RawTushareDailyBasic,
    RawTushareTradeCal,
)
from app.models.market import Stock, StockDaily
from app.models.index import IndexBasic, IndexDaily
from app.models.concept import ConceptIndex, ConceptDaily
from app.models.flow import MoneyFlow


class TestTimelineContinuity:
    """测试时间连续性。"""

    @pytest.mark.asyncio
    async def test_stock_daily_no_gap_in_recent_5_days(self):
        """测试最近 5 个交易日 stock_daily 无缺失。"""
        async with async_session_factory() as session:
            # 获取最近 5 个交易日
            stmt_dates = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(5)
            )
            result = await session.execute(stmt_dates)
            trade_dates = [row[0] for row in result]

            if len(trade_dates) < 5:
                pytest.skip("交易日历数据不足 5 天")

            # 检查每个交易日都有 stock_daily 数据
            for td_str in trade_dates:
                td_obj = date(int(td_str[:4]), int(td_str[4:6]), int(td_str[6:8]))
                stmt_count = select(func.count()).select_from(StockDaily).where(
                    StockDaily.trade_date == td_obj
                )
                result = await session.execute(stmt_count)
                count = result.scalar()

                assert count > 0, f"交易日 {td_str} 的 stock_daily 数据缺失"


class TestStockDailyIndexDailyConsistency:
    """测试 stock_daily 与 index_daily 交易日一致性。"""

    @pytest.mark.asyncio
    async def test_trade_date_match(self):
        """测试最近 5 个交易日两表覆盖一致。"""
        async with async_session_factory() as session:
            # stock_daily 最近 5 个交易日
            stmt_sd = (
                select(StockDaily.trade_date)
                .distinct()
                .order_by(StockDaily.trade_date.desc())
                .limit(5)
            )
            result = await session.execute(stmt_sd)
            sd_dates = {row[0] for row in result}

            # index_daily 最近 5 个交易日
            stmt_id = (
                select(IndexDaily.trade_date)
                .distinct()
                .order_by(IndexDaily.trade_date.desc())
                .limit(5)
            )
            result = await session.execute(stmt_id)
            id_dates = {row[0] for row in result}

            if not sd_dates or not id_dates:
                pytest.skip("stock_daily 或 index_daily 数据不足")

            assert sd_dates == id_dates, (
                f"交易日不一致，stock_daily 独有：{sd_dates - id_dates}，"
                f"index_daily 独有：{id_dates - sd_dates}"
            )


class TestStockDailyMoneyFlowConsistency:
    """测试 stock_daily 与 money_flow 交易日一致性。"""

    @pytest.mark.asyncio
    async def test_money_flow_dates_subset(self):
        """测试 money_flow 交易日是 stock_daily 交易日的子集。"""
        async with async_session_factory() as session:
            # stock_daily 最近 5 个交易日
            stmt_sd = (
                select(StockDaily.trade_date)
                .distinct()
                .order_by(StockDaily.trade_date.desc())
                .limit(5)
            )
            result = await session.execute(stmt_sd)
            sd_dates = {row[0] for row in result}

            # money_flow 最近 5 个交易日
            stmt_mf = (
                select(MoneyFlow.trade_date)
                .distinct()
                .order_by(MoneyFlow.trade_date.desc())
                .limit(5)
            )
            result = await session.execute(stmt_mf)
            mf_dates = {row[0] for row in result}

            if not mf_dates:
                pytest.skip("没有 money_flow 数据")

            extra = mf_dates - sd_dates
            assert len(extra) == 0, f"money_flow 存在 stock_daily 中没有的交易日：{extra}"


class TestTsCodeConsistency:
    """测试 ts_code 跨表一致性。"""

    @pytest.mark.asyncio
    async def test_stock_daily_ts_code_in_stocks(self):
        """测试 stock_daily 的 ts_code 全部在 stocks 表中。"""
        async with async_session_factory() as session:
            # 获取最近一个交易日
            stmt_max = select(func.max(StockDaily.trade_date))
            result = await session.execute(stmt_max)
            max_date = result.scalar()

            if not max_date:
                pytest.skip("没有 stock_daily 数据")

            # stock_daily 的 ts_code 集合
            stmt_sd_codes = select(StockDaily.ts_code).where(
                StockDaily.trade_date == max_date
            ).distinct()
            result = await session.execute(stmt_sd_codes)
            sd_codes = {row[0] for row in result}

            # stocks 表的 ts_code 集合
            stmt_stock_codes = select(Stock.ts_code).distinct()
            result = await session.execute(stmt_stock_codes)
            stock_codes = {row[0] for row in result}

            missing = sd_codes - stock_codes
            assert len(missing) == 0, f"stock_daily 中有 {len(missing)} 个 ts_code 不在 stocks 表中：{list(missing)[:5]}"


    @pytest.mark.asyncio
    async def test_index_daily_codes_in_index_basic(self):
        """测试 index_daily 的指数代码全部在 index_basic 中。"""
        async with async_session_factory() as session:
            stmt_max = select(func.max(IndexDaily.trade_date))
            result = await session.execute(stmt_max)
            max_date = result.scalar()

            if not max_date:
                pytest.skip("没有 index_daily 数据")

            stmt_id_codes = select(IndexDaily.ts_code).where(
                IndexDaily.trade_date == max_date
            ).distinct()
            result = await session.execute(stmt_id_codes)
            id_codes = {row[0] for row in result}

            stmt_ib_codes = select(IndexBasic.ts_code).distinct()
            result = await session.execute(stmt_ib_codes)
            ib_codes = {row[0] for row in result}

            missing = id_codes - ib_codes
            assert len(missing) == 0, f"index_daily 中有 {len(missing)} 个指数代码不在 index_basic 中：{list(missing)[:5]}"

    @pytest.mark.asyncio
    async def test_concept_daily_codes_in_concept_index(self):
        """测试 concept_daily 的板块代码全部在 concept_index 中。"""
        async with async_session_factory() as session:
            stmt_max = select(func.max(ConceptDaily.trade_date))
            result = await session.execute(stmt_max)
            max_date = result.scalar()

            if not max_date:
                pytest.skip("没有 concept_daily 数据")

            stmt_cd_codes = select(ConceptDaily.ts_code).where(
                ConceptDaily.trade_date == max_date
            ).distinct()
            result = await session.execute(stmt_cd_codes)
            cd_codes = {row[0] for row in result}

            stmt_ci_codes = select(ConceptIndex.ts_code).distinct()
            result = await session.execute(stmt_ci_codes)
            ci_codes = {row[0] for row in result}

            missing = cd_codes - ci_codes
            assert len(missing) == 0, f"concept_daily 中有 {len(missing)} 个板块代码不在 concept_index 中：{list(missing)[:5]}"


class TestRawDailyThreeTableJoin:
    """测试 raw_tushare_daily 三表 JOIN 完整性。"""

    @pytest.mark.asyncio
    async def test_join_match_rate(self):
        """测试 daily + adj_factor + daily_basic 三表 JOIN 匹配率 >= 95%。"""
        async with async_session_factory() as session:
            # 获取最近一个交易日
            stmt_recent = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有可用的交易日数据")

            # daily 记录数
            stmt_daily = select(func.count()).select_from(RawTushareDaily).where(
                RawTushareDaily.trade_date == trade_date
            )
            result = await session.execute(stmt_daily)
            daily_count = result.scalar()

            # adj_factor 记录数
            stmt_adj = select(func.count()).select_from(RawTushareAdjFactor).where(
                RawTushareAdjFactor.trade_date == trade_date
            )
            result = await session.execute(stmt_adj)
            adj_count = result.scalar()

            # daily_basic 记录数
            stmt_basic = select(func.count()).select_from(RawTushareDailyBasic).where(
                RawTushareDailyBasic.trade_date == trade_date
            )
            result = await session.execute(stmt_basic)
            basic_count = result.scalar()

            if daily_count == 0:
                pytest.skip("没有可用的 daily 数据")

            adj_ratio = adj_count / daily_count
            basic_ratio = basic_count / daily_count

            assert (
                adj_ratio >= 0.95
            ), f"adj_factor 匹配率 {adj_ratio:.2%} < 95%，daily={daily_count}, adj={adj_count}"
            assert (
                basic_ratio >= 0.95
            ), f"daily_basic 匹配率 {basic_ratio:.2%} < 95%，daily={daily_count}, basic={basic_count}"


class TestDataFreshness:
    """测试全链路数据新鲜度。"""

    @pytest.mark.asyncio
    async def test_business_tables_freshness(self):
        """测试各业务表最新数据在最近 3 个交易日内。"""
        async with async_session_factory() as session:
            # 获取最近第 3 个交易日
            stmt_dates = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(3)
            )
            result = await session.execute(stmt_dates)
            recent_dates = [row[0] for row in result]

            if len(recent_dates) < 3:
                pytest.skip("交易日历数据不足")

            threshold_str = recent_dates[-1]  # 第 3 个交易日
            threshold_date = date(
                int(threshold_str[:4]), int(threshold_str[4:6]), int(threshold_str[6:8])
            )

            # 检查各业务表
            tables = {
                "stock_daily": select(func.max(StockDaily.trade_date)),
                "index_daily": select(func.max(IndexDaily.trade_date)),
                "concept_daily": select(func.max(ConceptDaily.trade_date)),
                "money_flow": select(func.max(MoneyFlow.trade_date)),
            }

            for table_name, stmt in tables.items():
                result = await session.execute(stmt)
                max_date = result.scalar()

                if max_date is None:
                    pytest.skip(f"{table_name} 没有数据")

                assert (
                    max_date >= threshold_date
                ), f"{table_name} 最新数据 {max_date} 早于最近第 3 个交易日 {threshold_date}"
