"""P1 财务数据校验测试。

测试范围：
- raw_tushare_fina_indicator 数据完整性
- raw → finance_indicator ETL 转换正确性
- 财务数据质量
- 跨表一致性
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.raw import RawTushareFinaIndicator, RawTushareStockBasic
from app.models.finance import FinanceIndicator


class TestRawFinaIndicatorIntegrity:
    """测试 raw_tushare_fina_indicator 数据完整性。"""

    @pytest.mark.asyncio
    async def test_fina_indicator_record_count(self):
        """测试记录数 >= 预期季度数 × 上市公司数 × 0.95。

        假设：最近 1 年（4 个季度）的数据
        """
        async with async_session_factory() as session:
            # 获取上市公司数
            stmt_stock_count = select(func.count()).select_from(
                RawTushareStockBasic
            ).where(RawTushareStockBasic.list_status == "L")
            result = await session.execute(stmt_stock_count)
            stock_count = result.scalar()

            # 预期记录数：4 个季度 × 上市公司数 × 0.95
            expected_count = int(4 * stock_count * 0.95)

            # 获取最近 1 年的财务数据记录数
            one_year_ago = date.today().replace(year=date.today().year - 1)
            one_year_ago_str = one_year_ago.strftime("%Y%m%d")

            stmt_fina_count = select(func.count()).select_from(
                RawTushareFinaIndicator
            ).where(RawTushareFinaIndicator.end_date >= one_year_ago_str)
            result = await session.execute(stmt_fina_count)
            fina_count = result.scalar()

            assert (
                fina_count >= expected_count
            ), f"财务数据记录数 {fina_count} < 预期 {expected_count}（{stock_count} 公司 × 4 季度 × 0.95）"

    @pytest.mark.asyncio
    async def test_fina_indicator_has_recent_data(self):
        """测试是否有最近一个季度的数据。"""
        async with async_session_factory() as session:
            # 获取最新的报告期
            stmt_max_period = select(
                func.max(RawTushareFinaIndicator.end_date)
            ).select_from(RawTushareFinaIndicator)
            result = await session.execute(stmt_max_period)
            max_period = result.scalar()

            if not max_period:
                pytest.skip("没有财务数据")

            # 验证最新报告期在最近 6 个月内
            max_period_date = date(
                int(max_period[:4]), int(max_period[4:6]), int(max_period[6:8])
            )
            six_months_ago = date.today().replace(
                month=date.today().month - 6 if date.today().month > 6 else date.today().month + 6,
                year=date.today().year if date.today().month > 6 else date.today().year - 1,
            )

            assert (
                max_period_date >= six_months_ago
            ), f"最新财务数据报告期 {max_period} 过旧（超过 6 个月）"


class TestETLTransformCorrectness:
    """测试 raw → finance_indicator ETL 转换正确性。"""

    @pytest.mark.asyncio
    async def test_field_mapping(self):
        """测试字段映射正确性。"""
        async with async_session_factory() as session:
            # 获取一条 raw 记录
            stmt_raw = select(RawTushareFinaIndicator).limit(1)
            result = await session.execute(stmt_raw)
            raw_record = result.scalar_one_or_none()

            if not raw_record:
                pytest.skip("没有财务数据")

            # 获取对应的 finance_indicator 记录
            end_date_obj = date(
                int(raw_record.end_date[:4]),
                int(raw_record.end_date[4:6]),
                int(raw_record.end_date[6:8]),
            )
            stmt_finance = select(FinanceIndicator).where(
                FinanceIndicator.ts_code == raw_record.ts_code,
                FinanceIndicator.end_date == end_date_obj,
            )
            result = await session.execute(stmt_finance)
            finance_record = result.scalar_one_or_none()

            if not finance_record:
                pytest.skip("没有对应的 finance_indicator 数据")

            # 验证关键字段映射
            assert finance_record.ts_code == raw_record.ts_code
            assert finance_record.end_date == end_date_obj

            # 验证数值字段（如果 raw 有值，finance 也应该有值）
            if raw_record.roe is not None:
                assert finance_record.roe is not None, "roe 字段映射失败"

    @pytest.mark.asyncio
    async def test_date_format_conversion(self):
        """测试日期格式转换（YYYYMMDD → date）。"""
        async with async_session_factory() as session:
            # 获取一条 finance_indicator 记录
            stmt_finance = select(FinanceIndicator).limit(1)
            result = await session.execute(stmt_finance)
            finance_record = result.scalar_one_or_none()

            if not finance_record:
                pytest.skip("没有 finance_indicator 数据")

            # 验证日期字段是 date 类型
            assert isinstance(
                finance_record.end_date, date
            ), f"end_date 应该是 date 类型，实际是 {type(finance_record.end_date)}"
            assert isinstance(
                finance_record.ann_date, date
            ), f"ann_date 应该是 date 类型，实际是 {type(finance_record.ann_date)}"


class TestFinanceDataQuality:
    """测试财务数据质量。"""

    @pytest.mark.asyncio
    async def test_key_fields_non_null_rate(self):
        """测试关键字段非空率 >= 90%。"""
        async with async_session_factory() as session:
            # 获取最近一个报告期的数据
            stmt_max_period = select(
                func.max(RawTushareFinaIndicator.end_date)
            ).select_from(RawTushareFinaIndicator)
            result = await session.execute(stmt_max_period)
            max_period = result.scalar()

            if not max_period:
                pytest.skip("没有财务数据")

            # 获取该报告期的总记录数
            stmt_total = select(func.count()).select_from(
                RawTushareFinaIndicator
            ).where(RawTushareFinaIndicator.end_date == max_period)
            result = await session.execute(stmt_total)
            total_count = result.scalar()

            if total_count == 0:
                pytest.skip("没有可用的财务数据")

            # 检查关键字段的非空率
            key_fields = ["roe", "roa", "gross_margin", "netprofit_margin"]
            for field_name in key_fields:
                field = getattr(RawTushareFinaIndicator, field_name)
                stmt_non_null = select(func.count()).select_from(
                    RawTushareFinaIndicator
                ).where(
                    RawTushareFinaIndicator.end_date == max_period,
                    field.isnot(None),
                )
                result = await session.execute(stmt_non_null)
                non_null_count = result.scalar()

                non_null_rate = non_null_count / total_count
                assert (
                    non_null_rate >= 0.90
                ), f"{field_name} 非空率 {non_null_rate:.2%} < 90%"

    @pytest.mark.asyncio
    async def test_value_range_reasonability(self):
        """测试数值范围合理性。"""
        async with async_session_factory() as session:
            # 获取最近一个报告期的数据
            stmt_max_period = select(
                func.max(RawTushareFinaIndicator.end_date)
            ).select_from(RawTushareFinaIndicator)
            result = await session.execute(stmt_max_period)
            max_period = result.scalar()

            if not max_period:
                pytest.skip("没有财务数据")

            # 获取该报告期的数据
            stmt_fina = select(RawTushareFinaIndicator).where(
                RawTushareFinaIndicator.end_date == max_period,
                RawTushareFinaIndicator.roe.isnot(None),
            )
            result = await session.execute(stmt_fina)
            fina_records = result.scalars().all()

            if not fina_records:
                pytest.skip("没有可用的财务数据")

            # 检查 ROE 范围（-100% ~ 100%）
            invalid_roe_count = 0
            for record in fina_records:
                roe = Decimal(str(record.roe))
                if roe < -100 or roe > 100:
                    invalid_roe_count += 1

            invalid_roe_rate = invalid_roe_count / len(fina_records)
            assert (
                invalid_roe_rate <= 0.01
            ), f"ROE 超出合理范围的比例 {invalid_roe_rate:.2%} > 1%"


class TestCrossTableConsistency:
    """测试跨表一致性。"""

    @pytest.mark.asyncio
    async def test_raw_to_finance_indicator_record_match(self):
        """测试 raw 表和业务表记录数匹配度 >= 95%。"""
        async with async_session_factory() as session:
            # 获取最近一个报告期
            stmt_max_period = select(
                func.max(RawTushareFinaIndicator.end_date)
            ).select_from(RawTushareFinaIndicator)
            result = await session.execute(stmt_max_period)
            max_period = result.scalar()

            if not max_period:
                pytest.skip("没有财务数据")

            # 获取 raw 表记录数
            stmt_raw_count = select(func.count()).select_from(
                RawTushareFinaIndicator
            ).where(RawTushareFinaIndicator.end_date == max_period)
            result = await session.execute(stmt_raw_count)
            raw_count = result.scalar()

            # 获取 finance_indicator 表记录数
            max_period_date = date(
                int(max_period[:4]), int(max_period[4:6]), int(max_period[6:8])
            )
            stmt_finance_count = select(func.count()).select_from(
                FinanceIndicator
            ).where(FinanceIndicator.end_date == max_period_date)
            result = await session.execute(stmt_finance_count)
            finance_count = result.scalar()

            # 计算匹配度
            match_ratio = finance_count / raw_count if raw_count > 0 else 0
            assert (
                match_ratio >= 0.95
            ), f"记录数匹配度 {match_ratio:.2%} < 95%，raw={raw_count}, finance_indicator={finance_count}"
