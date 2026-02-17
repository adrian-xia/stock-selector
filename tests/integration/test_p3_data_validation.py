"""P3 指数数据校验测试。

测试范围：
- raw_tushare_index_daily 核心指数记录校验
- index_daily ETL 转换校验
- index_weight 权重校验
- index_basic 静态数据校验
- industry_classify 数据校验
"""

import pytest
from datetime import date
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.raw import (
    RawTushareIndexDaily,
    RawTushareIndexWeight,
    RawTushareIndexBasic,
    RawTushareIndexClassify,
)
from app.models.index import (
    IndexBasic,
    IndexDaily,
    IndexWeight,
    IndustryClassify,
)

# 核心指数列表
CORE_INDEX_CODES = [
    "000001.SH",  # 上证综指
    "399001.SZ",  # 深证成指
    "399006.SZ",  # 创业板指
    "000300.SH",  # 沪深300
    "000905.SH",  # 中证500
    "000852.SH",  # 中证1000
]


class TestRawIndexDailyIntegrity:
    """测试 raw_tushare_index_daily 数据完整性。"""

    @pytest.mark.asyncio
    async def test_core_index_coverage(self):
        """测试核心指数在最近交易日全部有记录。"""
        async with async_session_factory() as session:
            # 获取最近一个有数据的交易日
            stmt_recent = (
                select(RawTushareIndexDaily.trade_date)
                .group_by(RawTushareIndexDaily.trade_date)
                .order_by(RawTushareIndexDaily.trade_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有指数日线数据")

            # 检查核心指数是否全部有记录
            stmt_codes = select(RawTushareIndexDaily.ts_code).where(
                RawTushareIndexDaily.trade_date == trade_date
            )
            result = await session.execute(stmt_codes)
            available_codes = {row[0] for row in result}

            missing = [c for c in CORE_INDEX_CODES if c not in available_codes]
            assert len(missing) == 0, f"交易日 {trade_date} 缺少核心指数：{missing}"


class TestIndexDailyETLCorrectness:
    """测试 index_daily ETL 转换校验。"""

    @pytest.mark.asyncio
    async def test_field_mapping(self):
        """测试 raw → index_daily 字段映射。"""
        async with async_session_factory() as session:
            # 获取一条 raw 记录
            stmt_raw = select(RawTushareIndexDaily).limit(1)
            result = await session.execute(stmt_raw)
            raw_record = result.scalar_one_or_none()

            if not raw_record:
                pytest.skip("没有指数日线数据")

            trade_date_str = raw_record.trade_date
            trade_date_obj = date(
                int(trade_date_str[:4]), int(trade_date_str[4:6]), int(trade_date_str[6:8])
            )
            stmt_biz = select(IndexDaily).where(
                IndexDaily.ts_code == raw_record.ts_code,
                IndexDaily.trade_date == trade_date_obj,
            )
            result = await session.execute(stmt_biz)
            biz_record = result.scalar_one_or_none()

            if not biz_record:
                pytest.skip("没有对应的 index_daily 业务数据")

            assert biz_record.ts_code == raw_record.ts_code
            assert biz_record.trade_date == trade_date_obj
            assert isinstance(biz_record.trade_date, date)

    @pytest.mark.asyncio
    async def test_close_price_positive(self):
        """测试 index_daily 收盘价为正数。"""
        async with async_session_factory() as session:
            stmt_max_date = select(func.max(IndexDaily.trade_date))
            result = await session.execute(stmt_max_date)
            max_date = result.scalar()

            if not max_date:
                pytest.skip("没有 index_daily 数据")

            stmt = select(IndexDaily).where(
                IndexDaily.trade_date == max_date,
                IndexDaily.close.isnot(None),
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

            for record in records:
                assert record.close > 0, f"{record.ts_code} 收盘价 {record.close} <= 0"


class TestIndexWeightValidation:
    """测试 index_weight 数据校验。"""

    @pytest.mark.asyncio
    async def test_weight_sum_near_100(self):
        """测试成分股权重之和接近 100%。"""
        async with async_session_factory() as session:
            # 获取最近一个有权重数据的交易日
            stmt_max_date = select(func.max(IndexWeight.trade_date))
            result = await session.execute(stmt_max_date)
            max_date = result.scalar()

            if not max_date:
                pytest.skip("没有 index_weight 数据")

            # 检查沪深300的权重之和
            stmt_sum = select(func.sum(IndexWeight.weight)).where(
                IndexWeight.index_code == "000300.SH",
                IndexWeight.trade_date == max_date,
            )
            result = await session.execute(stmt_sum)
            weight_sum = result.scalar()

            if weight_sum is None:
                pytest.skip("没有沪深300权重数据")

            # 权重之和应在 90-110 之间（允许误差）
            assert (
                90 <= float(weight_sum) <= 110
            ), f"沪深300权重之和 {weight_sum} 不在 90-110 范围内"


class TestIndexBasicValidation:
    """测试 index_basic 静态数据校验。"""

    @pytest.mark.asyncio
    async def test_core_index_exist(self):
        """测试核心指数全部存在。"""
        async with async_session_factory() as session:
            stmt = select(IndexBasic.ts_code).where(
                IndexBasic.ts_code.in_(CORE_INDEX_CODES)
            )
            result = await session.execute(stmt)
            found_codes = {row[0] for row in result}

            missing = [c for c in CORE_INDEX_CODES if c not in found_codes]
            assert len(missing) == 0, f"index_basic 缺少核心指数：{missing}"

    @pytest.mark.asyncio
    async def test_name_non_null(self):
        """测试指数名称非空。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(IndexBasic).where(
                IndexBasic.name.is_(None)
            )
            result = await session.execute(stmt)
            null_count = result.scalar()

            assert null_count == 0, f"发现 {null_count} 条指数名称为空"


class TestIndustryClassifyValidation:
    """测试 industry_classify 数据校验。"""

    @pytest.mark.asyncio
    async def test_industry_count(self):
        """测试行业分类记录数 >= 20（申万一级行业数）。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(IndustryClassify)
            result = await session.execute(stmt)
            count = result.scalar()

            assert count >= 20, f"行业分类记录数 {count} < 20"

    @pytest.mark.asyncio
    async def test_industry_name_non_null(self):
        """测试行业名称非空。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(IndustryClassify).where(
                IndustryClassify.industry_name.is_(None)
            )
            result = await session.execute(stmt)
            null_count = result.scalar()

            assert null_count == 0, f"发现 {null_count} 条行业名称为空"
