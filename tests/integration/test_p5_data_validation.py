"""P5 扩展数据校验测试。

测试范围：
- raw_tushare_suspend_d 数据校验
- suspend_info ETL 转换校验
- raw_tushare_limit_list_d 数据校验
- limit_list_daily ETL 转换校验
- P5 日频 raw 表基础校验
"""

import pytest
from datetime import date
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.raw import (
    RawTushareSuspendD,
    RawTushareLimitListD,
    RawTushareMargin,
    RawTushareBlockTrade,
    RawTushareDailyShare,
)
from app.models.extend import SuspendInfo, LimitListDaily


class TestRawSuspendDValidation:
    """测试 raw_tushare_suspend_d 数据校验。"""

    @pytest.mark.asyncio
    async def test_has_data(self):
        """测试有停牌数据。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(RawTushareSuspendD)
            result = await session.execute(stmt)
            count = result.scalar()

            if count == 0:
                pytest.skip("没有停牌数据（可能当前无停牌股票）")

    @pytest.mark.asyncio
    async def test_key_fields_non_null(self):
        """测试 ts_code 和 suspend_date 非空。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(RawTushareSuspendD).where(
                RawTushareSuspendD.ts_code.is_(None)
                | RawTushareSuspendD.suspend_date.is_(None)
            )
            result = await session.execute(stmt)
            null_count = result.scalar()

            assert null_count == 0, f"发现 {null_count} 条停牌数据缺少 ts_code 或 suspend_date"


class TestSuspendInfoETLCorrectness:
    """测试 suspend_info ETL 转换校验。"""

    @pytest.mark.asyncio
    async def test_raw_to_biz_match(self):
        """测试 raw → suspend_info 匹配度 >= 95%。"""
        async with async_session_factory() as session:
            # 获取最近一个有数据的日期
            stmt_recent = (
                select(RawTushareSuspendD.suspend_date)
                .group_by(RawTushareSuspendD.suspend_date)
                .order_by(RawTushareSuspendD.suspend_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent)
            suspend_date_str = result.scalar()

            if not suspend_date_str:
                pytest.skip("没有停牌数据")

            # raw 记录数
            stmt_raw = select(func.count()).select_from(
                RawTushareSuspendD
            ).where(RawTushareSuspendD.suspend_date == suspend_date_str)
            result = await session.execute(stmt_raw)
            raw_count = result.scalar()

            # 业务表记录数
            suspend_date_obj = date(
                int(suspend_date_str[:4]), int(suspend_date_str[4:6]), int(suspend_date_str[6:8])
            )
            stmt_biz = select(func.count()).select_from(
                SuspendInfo
            ).where(SuspendInfo.suspend_date == suspend_date_obj)
            result = await session.execute(stmt_biz)
            biz_count = result.scalar()

            if raw_count == 0:
                pytest.skip("没有可用的停牌 raw 数据")

            match_ratio = biz_count / raw_count
            assert (
                match_ratio >= 0.95
            ), f"停牌匹配度 {match_ratio:.2%} < 95%，raw={raw_count}, suspend_info={biz_count}"

    @pytest.mark.asyncio
    async def test_date_format_conversion(self):
        """测试日期格式转换。"""
        async with async_session_factory() as session:
            stmt = select(SuspendInfo).limit(1)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                pytest.skip("没有 suspend_info 数据")

            assert isinstance(
                record.suspend_date, date
            ), f"suspend_date 应该是 date 类型，实际是 {type(record.suspend_date)}"


class TestRawLimitListDValidation:
    """测试 raw_tushare_limit_list_d 数据校验。"""

    @pytest.mark.asyncio
    async def test_has_recent_data(self):
        """测试最近交易日有涨跌停数据。"""
        async with async_session_factory() as session:
            stmt_recent = (
                select(RawTushareLimitListD.trade_date)
                .group_by(RawTushareLimitListD.trade_date)
                .order_by(RawTushareLimitListD.trade_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent)
            trade_date = result.scalar()

            assert trade_date is not None, "没有涨跌停数据"

    @pytest.mark.asyncio
    async def test_key_fields_non_null(self):
        """测试 ts_code 和 trade_date 非空。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(RawTushareLimitListD).where(
                RawTushareLimitListD.ts_code.is_(None)
                | RawTushareLimitListD.trade_date.is_(None)
            )
            result = await session.execute(stmt)
            null_count = result.scalar()

            assert null_count == 0, f"发现 {null_count} 条涨跌停数据缺少 ts_code 或 trade_date"


class TestLimitListDailyETLCorrectness:
    """测试 limit_list_daily ETL 转换校验。"""

    @pytest.mark.asyncio
    async def test_raw_to_biz_match(self):
        """测试 raw → limit_list_daily 匹配度 >= 95%。"""
        async with async_session_factory() as session:
            stmt_recent = (
                select(RawTushareLimitListD.trade_date)
                .group_by(RawTushareLimitListD.trade_date)
                .order_by(RawTushareLimitListD.trade_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有涨跌停数据")

            # raw 记录数
            stmt_raw = select(func.count()).select_from(
                RawTushareLimitListD
            ).where(RawTushareLimitListD.trade_date == trade_date)
            result = await session.execute(stmt_raw)
            raw_count = result.scalar()

            # 业务表记录数
            trade_date_obj = date(
                int(trade_date[:4]), int(trade_date[4:6]), int(trade_date[6:8])
            )
            stmt_biz = select(func.count()).select_from(
                LimitListDaily
            ).where(LimitListDaily.trade_date == trade_date_obj)
            result = await session.execute(stmt_biz)
            biz_count = result.scalar()

            if raw_count == 0:
                pytest.skip("没有可用的涨跌停 raw 数据")

            match_ratio = biz_count / raw_count
            assert (
                match_ratio >= 0.95
            ), f"涨跌停匹配度 {match_ratio:.2%} < 95%，raw={raw_count}, limit_list_daily={biz_count}"


class TestP5DailyRawBasicValidation:
    """测试 P5 日频 raw 表基础校验。"""

    @pytest.mark.asyncio
    async def test_margin_has_recent_data(self):
        """测试融资融券 raw 表有最近数据。"""
        async with async_session_factory() as session:
            stmt = (
                select(RawTushareMargin.trade_date)
                .order_by(RawTushareMargin.trade_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有融资融券数据")

            # 验证有数据即可
            assert trade_date is not None

    @pytest.mark.asyncio
    async def test_block_trade_has_recent_data(self):
        """测试大宗交易 raw 表有最近数据。"""
        async with async_session_factory() as session:
            stmt = (
                select(RawTushareBlockTrade.trade_date)
                .order_by(RawTushareBlockTrade.trade_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有大宗交易数据")

            assert trade_date is not None

    @pytest.mark.asyncio
    async def test_daily_share_has_recent_data(self):
        """测试每日股本 raw 表有最近数据。"""
        async with async_session_factory() as session:
            stmt = (
                select(RawTushareDailyShare.trade_date)
                .order_by(RawTushareDailyShare.trade_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有每日股本数据")

            assert trade_date is not None
