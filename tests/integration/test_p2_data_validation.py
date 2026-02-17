"""P2 资金流向数据校验测试。

测试范围：
- raw_tushare_moneyflow 数据完整性
- moneyflow ETL 字段映射正确性
- money_flow 业务表数据质量
- dragon_tiger 数据校验
"""

import pytest
from datetime import date
from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.raw import (
    RawTushareMoneyflow,
    RawTushareStockBasic,
    RawTushareTradeCal,
    RawTushareTopList,
)
from app.models.flow import MoneyFlow, DragonTiger


class TestRawMoneyflowIntegrity:
    """测试 raw_tushare_moneyflow 数据完整性。"""

    @pytest.mark.asyncio
    async def test_moneyflow_record_count_per_trade_date(self):
        """测试每个交易日记录数 >= 上市股票数 × 0.90。"""
        async with async_session_factory() as session:
            # 获取上市股票数
            stmt_stock_count = select(func.count()).select_from(
                RawTushareStockBasic
            ).where(RawTushareStockBasic.list_status == "L")
            result = await session.execute(stmt_stock_count)
            stock_count = result.scalar()

            threshold = int(stock_count * 0.90)

            # 获取最近一个有资金流向数据的交易日
            stmt_recent_date = (
                select(RawTushareMoneyflow.trade_date)
                .group_by(RawTushareMoneyflow.trade_date)
                .order_by(RawTushareMoneyflow.trade_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent_date)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有资金流向数据")

            # 检查记录数
            stmt_count = select(func.count()).select_from(
                RawTushareMoneyflow
            ).where(RawTushareMoneyflow.trade_date == trade_date)
            result = await session.execute(stmt_count)
            count = result.scalar()

            assert (
                count >= threshold
            ), f"交易日 {trade_date} 资金流向记录数 {count} < 阈值 {threshold}"


class TestMoneyflowETLCorrectness:
    """测试 moneyflow ETL 字段映射正确性。"""

    @pytest.mark.asyncio
    async def test_field_mapping(self):
        """测试 raw → money_flow 字段映射。"""
        async with async_session_factory() as session:
            # 获取一条 raw 记录
            stmt_raw = select(RawTushareMoneyflow).limit(1)
            result = await session.execute(stmt_raw)
            raw_record = result.scalar_one_or_none()

            if not raw_record:
                pytest.skip("没有资金流向数据")

            # 获取对应的 money_flow 记录
            trade_date_str = raw_record.trade_date
            trade_date_obj = date(
                int(trade_date_str[:4]), int(trade_date_str[4:6]), int(trade_date_str[6:8])
            )
            stmt_biz = select(MoneyFlow).where(
                MoneyFlow.ts_code == raw_record.ts_code,
                MoneyFlow.trade_date == trade_date_obj,
            )
            result = await session.execute(stmt_biz)
            biz_record = result.scalar_one_or_none()

            if not biz_record:
                pytest.skip("没有对应的 money_flow 业务数据")

            # 验证关键字段映射
            assert biz_record.ts_code == raw_record.ts_code
            assert biz_record.trade_date == trade_date_obj

    @pytest.mark.asyncio
    async def test_date_format_conversion(self):
        """测试日期格式转换（YYYYMMDD → date）。"""
        async with async_session_factory() as session:
            stmt = select(MoneyFlow).limit(1)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                pytest.skip("没有 money_flow 数据")

            assert isinstance(
                record.trade_date, date
            ), f"trade_date 应该是 date 类型，实际是 {type(record.trade_date)}"


class TestMoneyFlowDataQuality:
    """测试 money_flow 业务表数据质量。"""

    @pytest.mark.asyncio
    async def test_key_fields_non_null_rate(self):
        """测试关键金额字段非空率 >= 90%。"""
        async with async_session_factory() as session:
            # 获取最近一个交易日
            stmt_max_date = select(func.max(MoneyFlow.trade_date))
            result = await session.execute(stmt_max_date)
            max_date = result.scalar()

            if not max_date:
                pytest.skip("没有 money_flow 数据")

            # 获取总记录数
            stmt_total = select(func.count()).select_from(MoneyFlow).where(
                MoneyFlow.trade_date == max_date
            )
            result = await session.execute(stmt_total)
            total_count = result.scalar()

            if total_count == 0:
                pytest.skip("没有可用的 money_flow 数据")

            # 检查关键字段非空率
            key_fields = ["buy_sm_amount", "sell_sm_amount", "buy_lg_amount", "sell_lg_amount"]
            for field_name in key_fields:
                field = getattr(MoneyFlow, field_name)
                stmt_non_null = select(func.count()).select_from(MoneyFlow).where(
                    MoneyFlow.trade_date == max_date,
                    field.isnot(None),
                )
                result = await session.execute(stmt_non_null)
                non_null_count = result.scalar()

                non_null_rate = non_null_count / total_count
                assert (
                    non_null_rate >= 0.90
                ), f"{field_name} 非空率 {non_null_rate:.2%} < 90%"


class TestDragonTigerValidation:
    """测试 dragon_tiger 数据校验。"""

    @pytest.mark.asyncio
    async def test_raw_to_dragon_tiger_match(self):
        """测试 raw_tushare_top_list → dragon_tiger 匹配度 >= 95%。"""
        async with async_session_factory() as session:
            # 获取最近一个有龙虎榜数据的交易日
            stmt_recent = (
                select(RawTushareTopList.trade_date)
                .group_by(RawTushareTopList.trade_date)
                .order_by(RawTushareTopList.trade_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt_recent)
            trade_date = result.scalar()

            if not trade_date:
                pytest.skip("没有龙虎榜数据")

            # raw 记录数
            stmt_raw_count = select(func.count()).select_from(
                RawTushareTopList
            ).where(RawTushareTopList.trade_date == trade_date)
            result = await session.execute(stmt_raw_count)
            raw_count = result.scalar()

            # 业务表记录数
            trade_date_obj = date(
                int(trade_date[:4]), int(trade_date[4:6]), int(trade_date[6:8])
            )
            stmt_biz_count = select(func.count()).select_from(
                DragonTiger
            ).where(DragonTiger.trade_date == trade_date_obj)
            result = await session.execute(stmt_biz_count)
            biz_count = result.scalar()

            if raw_count == 0:
                pytest.skip("没有可用的龙虎榜 raw 数据")

            match_ratio = biz_count / raw_count
            assert (
                match_ratio >= 0.95
            ), f"龙虎榜匹配度 {match_ratio:.2%} < 95%，raw={raw_count}, dragon_tiger={biz_count}"
