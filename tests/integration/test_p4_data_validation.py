"""P4 板块数据校验测试。

测试范围：
- concept_index 数据校验
- concept_daily 记录数校验
- concept_member 数据校验
- concept_daily ETL 转换校验
"""

import pytest
from datetime import date
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.raw import RawTushareThsDaily
from app.models.concept import ConceptIndex, ConceptDaily, ConceptMember


class TestConceptIndexValidation:
    """测试 concept_index 数据校验。"""

    @pytest.mark.asyncio
    async def test_concept_count(self):
        """测试板块数 >= 100。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(ConceptIndex)
            result = await session.execute(stmt)
            count = result.scalar()

            assert count >= 100, f"板块数 {count} < 100"

    @pytest.mark.asyncio
    async def test_concept_name_non_null(self):
        """测试板块名称非空。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(ConceptIndex).where(
                ConceptIndex.name.is_(None)
            )
            result = await session.execute(stmt)
            null_count = result.scalar()

            assert null_count == 0, f"发现 {null_count} 条板块名称为空"


class TestConceptDailyValidation:
    """测试 concept_daily 数据校验。"""

    @pytest.mark.asyncio
    async def test_record_count_per_trade_date(self):
        """测试每个交易日记录数 >= 板块数 × 0.90。"""
        async with async_session_factory() as session:
            # 获取板块总数
            stmt_concept_count = select(func.count()).select_from(ConceptIndex)
            result = await session.execute(stmt_concept_count)
            concept_count = result.scalar()

            if concept_count == 0:
                pytest.skip("没有板块数据")

            threshold = int(concept_count * 0.90)

            # 获取最近一个有数据的交易日
            stmt_max_date = select(func.max(ConceptDaily.trade_date))
            result = await session.execute(stmt_max_date)
            max_date = result.scalar()

            if not max_date:
                pytest.skip("没有 concept_daily 数据")

            stmt_count = select(func.count()).select_from(ConceptDaily).where(
                ConceptDaily.trade_date == max_date
            )
            result = await session.execute(stmt_count)
            count = result.scalar()

            assert (
                count >= threshold
            ), f"交易日 {max_date} 板块日线记录数 {count} < 阈值 {threshold}"

    @pytest.mark.asyncio
    async def test_etl_field_mapping(self):
        """测试 raw → concept_daily ETL 字段映射。"""
        async with async_session_factory() as session:
            # 获取一条 raw 记录
            stmt_raw = select(RawTushareThsDaily).limit(1)
            result = await session.execute(stmt_raw)
            raw_record = result.scalar_one_or_none()

            if not raw_record:
                pytest.skip("没有板块日线 raw 数据")

            trade_date_str = raw_record.trade_date
            trade_date_obj = date(
                int(trade_date_str[:4]), int(trade_date_str[4:6]), int(trade_date_str[6:8])
            )
            stmt_biz = select(ConceptDaily).where(
                ConceptDaily.ts_code == raw_record.ts_code,
                ConceptDaily.trade_date == trade_date_obj,
            )
            result = await session.execute(stmt_biz)
            biz_record = result.scalar_one_or_none()

            if not biz_record:
                pytest.skip("没有对应的 concept_daily 业务数据")

            assert biz_record.ts_code == raw_record.ts_code
            assert biz_record.trade_date == trade_date_obj
            assert isinstance(biz_record.trade_date, date)


class TestConceptMemberValidation:
    """测试 concept_member 数据校验。"""

    @pytest.mark.asyncio
    async def test_member_count(self):
        """测试成分股记录数 >= 1000。"""
        async with async_session_factory() as session:
            stmt = select(func.count()).select_from(ConceptMember)
            result = await session.execute(stmt)
            count = result.scalar()

            assert count >= 1000, f"板块成分股记录数 {count} < 1000"

    @pytest.mark.asyncio
    async def test_ts_code_format(self):
        """测试 ts_code 格式正确（6位数字.SH/SZ）。"""
        async with async_session_factory() as session:
            import re
            pattern = re.compile(r"^\d{6}\.(SH|SZ|BJ)$")

            stmt = select(ConceptMember.ts_code).distinct().limit(100)
            result = await session.execute(stmt)
            codes = [row[0] for row in result]

            if not codes:
                pytest.skip("没有板块成分股数据")

            invalid = [c for c in codes if not pattern.match(c)]
            assert len(invalid) == 0, f"发现格式错误的 ts_code：{invalid[:5]}"
