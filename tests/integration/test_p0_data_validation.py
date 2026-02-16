"""P0 核心数据校验测试。

测试范围：
- raw_tushare_stock_basic 数据完整性
- raw_tushare_trade_cal 数据完整性
- raw_tushare_daily 数据完整性
- raw → stock_daily ETL 转换正确性
- 跨表一致性
- 数据质量
- 涨跌停价格合理性
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.raw import (
    RawTushareStockBasic,
    RawTushareTradeCal,
    RawTushareDaily,
    RawTushareAdjFactor,
    RawTushareDailyBasic,
    RawTushareStkLimit,
)
from app.models.market import Stock, StockDaily


class TestRawStockBasicIntegrity:
    """测试 raw_tushare_stock_basic 数据完整性。"""

    @pytest.mark.asyncio
    async def test_stock_count_threshold(self):
        """测试上市股票数 >= 5000。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(RawTushareStockBasic)
            result = await session.execute(stmt)
            count = result.scalar()

            assert count >= 5000, f"上市股票数 {count} < 5000"

    @pytest.mark.asyncio
    async def test_listed_stocks_have_list_date(self):
        """测试上市股票必须有上市日期。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(RawTushareStockBasic).where(
                RawTushareStockBasic.list_status == "L",
                RawTushareStockBasic.list_date.is_(None),
            )
            result = await session.execute(stmt)
            count = result.scalar()

            assert count == 0, f"发现 {count} 只上市股票缺少上市日期"


class TestRawTradeCalIntegrity:
    """测试 raw_tushare_trade_cal 数据完整性。"""

    @pytest.mark.asyncio
    async def test_future_calendar_coverage(self):
        """测试交易日历覆盖未来 90 天。"""
        async with async_session_factory() as session:
            today = date.today()
            future_90_days = today + timedelta(days=90)
            future_90_days_str = future_90_days.strftime("%Y%m%d")

            stmt = select(func.max(RawTushareTradeCal.cal_date)).where(
                RawTushareTradeCal.exchange == "SSE"
            )
            result = await session.execute(stmt)
            max_date_str = result.scalar()

            assert (
                max_date_str >= future_90_days_str
            ), f"交易日历最大日期 {max_date_str} < 未来 90 天 {future_90_days_str}"

    @pytest.mark.asyncio
    async def test_trade_calendar_consistency(self):
        """测试上交所和深交所交易日历一致性。"""
        async with async_session_factory() as session:
            # 获取上交所交易日
            stmt_sse = select(RawTushareTradeCal.cal_date).where(
                RawTushareTradeCal.exchange == "SSE",
                RawTushareTradeCal.is_open == "1",
            )
            result_sse = await session.execute(stmt_sse)
            sse_dates = {row[0] for row in result_sse}

            # 获取深交所交易日
            stmt_szse = select(RawTushareTradeCal.cal_date).where(
                RawTushareTradeCal.exchange == "SZSE",
                RawTushareTradeCal.is_open == "1",
            )
            result_szse = await session.execute(stmt_szse)
            szse_dates = {row[0] for row in result_szse}

            # 计算差异
            diff = sse_dates.symmetric_difference(szse_dates)
            assert len(diff) == 0, f"上交所和深交所交易日不一致，差异 {len(diff)} 天"


class TestRawDailyIntegrity:
    """测试 raw_tushare_daily 数据完整性。"""

    @pytest.mark.asyncio
    async def test_daily_record_count_per_trade_date(self):
        """测试每个交易日记录数 >= 上市股票数 × 0.95。"""
        async with async_session_factory() as session:
            # 获取上市股票数
            stmt_stock_count = select(func.count()).select_from(
                RawTushareStockBasic
            ).where(RawTushareStockBasic.list_status == "L")
            result = await session.execute(stmt_stock_count)
            stock_count = result.scalar()

            threshold = int(stock_count * 0.95)

            # 获取最近 5 个交易日
            stmt_recent_dates = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(5)
            )
            result = await session.execute(stmt_recent_dates)
            recent_dates = [row[0] for row in result]

            # 检查每个交易日的记录数
            for trade_date in recent_dates:
                stmt_daily_count = select(func.count()).select_from(
                    RawTushareDaily
                ).where(RawTushareDaily.trade_date == trade_date)
                result = await session.execute(stmt_daily_count)
                daily_count = result.scalar()

                assert (
                    daily_count >= threshold
                ), f"交易日 {trade_date} 记录数 {daily_count} < 阈值 {threshold}"


class TestETLTransformCorrectness:
    """测试 raw → stock_daily ETL 转换正确性。"""

    @pytest.mark.asyncio
    async def test_amount_unit_conversion(self):
        """测试 amount 千元→元转换。"""
        async with async_session_factory() as session:
            # 获取最近一个交易日
            stmt_recent_date = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent_date)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有可用的交易日数据")

            # 获取 raw 表中的一条记录
            stmt_raw = (
                select(RawTushareDaily)
                .where(RawTushareDaily.trade_date == trade_date)
                .limit(1)
            )
            result = await session.execute(stmt_raw)
            raw_record = result.scalar_one_or_none()

            if not raw_record or raw_record.amount is None:
                pytest.skip("没有可用的 raw 数据")

            # 获取对应的 stock_daily 记录
            trade_date_obj = date(
                int(trade_date[:4]), int(trade_date[4:6]), int(trade_date[6:8])
            )
            stmt_stock_daily = select(StockDaily).where(
                StockDaily.ts_code == raw_record.ts_code,
                StockDaily.trade_date == trade_date_obj,
            )
            result = await session.execute(stmt_stock_daily)
            stock_daily_record = result.scalar_one_or_none()

            if not stock_daily_record:
                pytest.skip("没有对应的 stock_daily 数据")

            # 验证转换：raw.amount (千元) * 1000 = stock_daily.amount (元)
            expected_amount = Decimal(str(raw_record.amount)) * 1000
            actual_amount = stock_daily_record.amount

            # 允许 1% 误差
            diff_ratio = abs(actual_amount - expected_amount) / expected_amount
            assert (
                diff_ratio <= 0.01
            ), f"amount 转换错误：raw={raw_record.amount}, expected={expected_amount}, actual={actual_amount}"

    @pytest.mark.asyncio
    async def test_adj_factor_application(self):
        """测试复权因子应用。"""
        async with async_session_factory() as session:
            # 获取最近一个交易日
            stmt_recent_date = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent_date)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有可用的交易日数据")

            # 获取有复权因子的股票
            stmt_with_adj = (
                select(RawTushareDaily.ts_code)
                .join(
                    RawTushareAdjFactor,
                    (RawTushareDaily.ts_code == RawTushareAdjFactor.ts_code)
                    & (RawTushareDaily.trade_date == RawTushareAdjFactor.trade_date),
                )
                .where(
                    RawTushareDaily.trade_date == trade_date,
                    RawTushareAdjFactor.adj_factor.isnot(None),
                )
                .limit(1)
            )
            result = await session.execute(stmt_with_adj)
            ts_code = result.scalar_one_or_none()

            if not ts_code:
                pytest.skip("没有可用的复权因子数据")

            # 获取 stock_daily 记录
            trade_date_obj = date(
                int(trade_date[:4]), int(trade_date[4:6]), int(trade_date[6:8])
            )
            stmt_stock_daily = select(StockDaily).where(
                StockDaily.ts_code == ts_code,
                StockDaily.trade_date == trade_date_obj,
            )
            result = await session.execute(stmt_stock_daily)
            stock_daily_record = result.scalar_one_or_none()

            # 验证 adj_factor 字段存在且不为空
            assert (
                stock_daily_record is not None
            ), f"stock_daily 中找不到 {ts_code} 在 {trade_date} 的记录"
            assert (
                stock_daily_record.adj_factor is not None
            ), f"stock_daily.adj_factor 为空"


class TestCrossTableConsistency:
    """测试跨表一致性。"""

    @pytest.mark.asyncio
    async def test_raw_to_stock_daily_record_match(self):
        """测试 raw_tushare_daily + raw_tushare_adj_factor + raw_tushare_daily_basic → stock_daily 记录数匹配。"""
        async with async_session_factory() as session:
            # 获取最近一个交易日
            stmt_recent_date = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent_date)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有可用的交易日数据")

            # 获取 raw_tushare_daily 记录数
            stmt_raw_count = select(func.count()).select_from(RawTushareDaily).where(
                RawTushareDaily.trade_date == trade_date
            )
            result = await session.execute(stmt_raw_count)
            raw_count = result.scalar()

            # 获取 stock_daily 记录数
            trade_date_obj = date(
                int(trade_date[:4]), int(trade_date[4:6]), int(trade_date[6:8])
            )
            stmt_stock_daily_count = select(func.count()).select_from(
                StockDaily
            ).where(StockDaily.trade_date == trade_date_obj)
            result = await session.execute(stmt_stock_daily_count)
            stock_daily_count = result.scalar()

            # 允许 5% 差异（考虑退市股票等）
            match_ratio = stock_daily_count / raw_count if raw_count > 0 else 0
            assert (
                match_ratio >= 0.95
            ), f"记录数匹配度 {match_ratio:.2%} < 95%，raw={raw_count}, stock_daily={stock_daily_count}"


class TestDataQuality:
    """测试数据质量。"""

    @pytest.mark.asyncio
    async def test_stock_daily_key_fields_non_null_rate(self):
        """测试 stock_daily 关键字段 open/high/low/close 非空率 >= 99%。"""
        async with async_session_factory() as session:
            # 获取最近一个交易日
            stmt_recent_date = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent_date)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有可用的交易日数据")

            trade_date_obj = date(
                int(trade_date[:4]), int(trade_date[4:6]), int(trade_date[6:8])
            )

            # 获取总记录数
            stmt_total = select(func.count()).select_from(StockDaily).where(
                StockDaily.trade_date == trade_date_obj
            )
            result = await session.execute(stmt_total)
            total_count = result.scalar()

            if total_count == 0:
                pytest.skip("没有可用的 stock_daily 数据")

            # 检查每个关键字段的非空率
            for field_name in ["open", "high", "low", "close"]:
                field = getattr(StockDaily, field_name)
                stmt_non_null = select(func.count()).select_from(StockDaily).where(
                    StockDaily.trade_date == trade_date_obj, field.isnot(None)
                )
                result = await session.execute(stmt_non_null)
                non_null_count = result.scalar()

                non_null_rate = non_null_count / total_count
                assert (
                    non_null_rate >= 0.99
                ), f"{field_name} 非空率 {non_null_rate:.2%} < 99%"


class TestPriceLimitReasonability:
    """测试涨跌停价格合理性。"""

    @pytest.mark.asyncio
    async def test_limit_price_vs_pre_close(self):
        """测试 raw_tushare_stk_limit 涨停价 >= 昨收价，跌停价 <= 昨收价。"""
        async with async_session_factory() as session:
            # 获取最近一个交易日
            stmt_recent_date = (
                select(RawTushareTradeCal.cal_date)
                .where(
                    RawTushareTradeCal.exchange == "SSE",
                    RawTushareTradeCal.is_open == "1",
                    RawTushareTradeCal.cal_date <= date.today().strftime("%Y%m%d"),
                )
                .order_by(RawTushareTradeCal.cal_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent_date)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有可用的交易日数据")

            # 获取涨跌停数据
            stmt_limit = select(RawTushareStkLimit).where(
                RawTushareStkLimit.trade_date == trade_date,
                RawTushareStkLimit.up_limit.isnot(None),
                RawTushareStkLimit.down_limit.isnot(None),
                RawTushareStkLimit.pre_close.isnot(None),
            )
            result = await session.execute(stmt_limit)
            limit_records = result.scalars().all()

            if not limit_records:
                pytest.skip("没有可用的涨跌停数据")

            # 检查前 10 条记录
            for record in limit_records[:10]:
                up_limit = Decimal(str(record.up_limit))
                down_limit = Decimal(str(record.down_limit))
                pre_close = Decimal(str(record.pre_close))

                assert (
                    up_limit >= pre_close
                ), f"{record.ts_code} 涨停价 {up_limit} < 昨收价 {pre_close}"
                assert (
                    down_limit <= pre_close
                ), f"{record.ts_code} 跌停价 {down_limit} > 昨收价 {pre_close}"
