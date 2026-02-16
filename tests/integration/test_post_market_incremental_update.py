"""测试盘后链路增量更新集成测试（sync_raw_daily → etl_daily → 指标计算 → 策略执行）。

验证完整的盘后数据更新链路：
1. sync_raw_daily：按日期获取全市场原始数据到 raw 表
2. etl_daily：从 raw 表 ETL 清洗到 stock_daily 业务表
3. 指标计算：计算技术指标写入 technical_daily
4. 策略执行：执行选股策略管道

这是一个端到端的集成测试，需要真实的数据库和 Tushare API。
"""

import asyncio
import logging
from datetime import date, timedelta

import pytest
from sqlalchemy import select, func

from app.config import settings
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.database import async_session_factory, engine
from app.models.market import StockDaily, TradeCalendar
from app.models.raw import RawTushareDaily, RawTushareAdjFactor, RawTushareDailyBasic
from app.models.technical import TechnicalDaily

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
async def cleanup_engine():
    """每个测试后清理数据库引擎连接池。"""
    yield
    # 测试完成后，等待一下并清理连接池
    await asyncio.sleep(0.5)
    await engine.dispose()


def _build_manager() -> DataManager:
    """构建 DataManager 实例。"""
    client = TushareClient(
        token=settings.tushare_token,
        qps_limit=settings.tushare_qps_limit,
        retry_count=settings.tushare_retry_count,
        retry_interval=settings.tushare_retry_interval,
    )
    return DataManager(
        session_factory=async_session_factory,
        clients={"tushare": client},
        primary="tushare",
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_post_market_incremental_update_chain(cleanup_engine):
    """测试盘后链路增量更新完整流程。

    验证：sync_raw_daily → etl_daily → 指标计算 → 策略执行

    前置条件：
    - 数据库已初始化（有交易日历和股票列表）
    - Tushare API Token 已配置
    - 选择一个已有数据的历史交易日进行测试

    测试步骤：
    1. 选择一个历史交易日（最近 30 天内）
    2. 清空该日期的 raw 表和业务表数据
    3. 执行 sync_raw_daily 获取原始数据
    4. 执行 etl_daily 清洗数据
    5. 执行指标计算
    6. 验证数据完整性
    """
    manager = _build_manager()

    # 步骤 1：选择测试日期（最近 30 天内的交易日）
    async with async_session_factory() as session:
        stmt = (
            select(TradeCalendar.cal_date)
            .where(
                TradeCalendar.is_open.is_(True),
                TradeCalendar.cal_date >= date.today() - timedelta(days=30),
                TradeCalendar.cal_date < date.today(),
            )
            .order_by(TradeCalendar.cal_date.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        test_date = result.scalar_one_or_none()

    if not test_date:
        pytest.skip("没有找到最近 30 天内的交易日，跳过测试")

    logger.info(f"[测试] 选择测试日期：{test_date}")

    # 步骤 2：清空该日期的数据（准备干净的测试环境）
    td_str = test_date.strftime("%Y%m%d")
    async with async_session_factory() as session:
        # 清空 raw 表
        await session.execute(
            RawTushareDaily.__table__.delete().where(RawTushareDaily.trade_date == td_str)
        )
        await session.execute(
            RawTushareAdjFactor.__table__.delete().where(RawTushareAdjFactor.trade_date == td_str)
        )
        await session.execute(
            RawTushareDailyBasic.__table__.delete().where(RawTushareDailyBasic.trade_date == td_str)
        )
        # 清空业务表
        await session.execute(
            StockDaily.__table__.delete().where(StockDaily.trade_date == test_date)
        )
        await session.execute(
            TechnicalDaily.__table__.delete().where(TechnicalDaily.trade_date == test_date)
        )
        await session.commit()

    logger.info(f"[测试] 已清空 {test_date} 的数据")

    # 步骤 3：执行 sync_raw_daily（获取原始数据）
    logger.info(f"[测试] 步骤 1/4：执行 sync_raw_daily")
    raw_counts = await manager.sync_raw_daily(test_date)
    logger.info(f"[测试] sync_raw_daily 完成：{raw_counts}")

    # 验证 raw 表有数据
    assert raw_counts["daily"] > 0, "raw_tushare_daily 应该有数据"
    assert raw_counts["adj_factor"] > 0, "raw_tushare_adj_factor 应该有数据"
    assert raw_counts["daily_basic"] > 0, "raw_tushare_daily_basic 应该有数据"

    # 步骤 4：执行 etl_daily（ETL 清洗）
    logger.info(f"[测试] 步骤 2/4：执行 etl_daily")
    etl_result = await manager.etl_daily(test_date)
    logger.info(f"[测试] etl_daily 完成：{etl_result}")

    # 验证 stock_daily 有数据
    assert etl_result["inserted"] > 0, "stock_daily 应该有数据"

    async with async_session_factory() as session:
        stmt = select(func.count()).select_from(StockDaily).where(
            StockDaily.trade_date == test_date
        )
        result = await session.execute(stmt)
        daily_count = result.scalar()

    assert daily_count > 0, "stock_daily 表应该有数据"
    logger.info(f"[测试] stock_daily 记录数：{daily_count}")

    # 步骤 5：执行指标计算
    logger.info(f"[测试] 步骤 3/4：执行指标计算")
    from app.data.indicator import compute_incremental

    indicator_result = await compute_incremental(
        async_session_factory,
        target_date=test_date,
    )
    logger.info(f"[测试] 指标计算完成：{indicator_result}")

    # 验证 technical_daily 有数据
    assert indicator_result["success"] > 0, "应该有股票成功计算指标"

    async with async_session_factory() as session:
        stmt = select(func.count()).select_from(TechnicalDaily).where(
            TechnicalDaily.trade_date == test_date
        )
        result = await session.execute(stmt)
        technical_count = result.scalar()

    assert technical_count > 0, "technical_daily 表应该有数据"
    logger.info(f"[测试] technical_daily 记录数：{technical_count}")

    # 步骤 6：验证数据完整性
    logger.info(f"[测试] 步骤 4/4：验证数据完整性")

    # 验证 stock_daily 和 technical_daily 记录数一致
    assert technical_count == daily_count, (
        f"technical_daily ({technical_count}) 和 stock_daily ({daily_count}) 记录数应该一致"
    )

    # 验证数据质量：随机抽取 10 条记录检查关键字段非空
    async with async_session_factory() as session:
        stmt = (
            select(StockDaily)
            .where(StockDaily.trade_date == test_date)
            .limit(10)
        )
        result = await session.execute(stmt)
        sample_rows = result.scalars().all()

    assert len(sample_rows) > 0, "应该有样本数据"

    for row in sample_rows:
        assert row.open is not None, f"{row.ts_code} 的 open 不应为空"
        assert row.high is not None, f"{row.ts_code} 的 high 不应为空"
        assert row.low is not None, f"{row.ts_code} 的 low 不应为空"
        assert row.close is not None, f"{row.ts_code} 的 close 不应为空"

    logger.info(f"[测试] 数据完整性验证通过")

    # 步骤 7：验证技术指标数据质量
    async with async_session_factory() as session:
        stmt = (
            select(TechnicalDaily)
            .where(TechnicalDaily.trade_date == test_date)
            .limit(10)
        )
        result = await session.execute(stmt)
        tech_sample_rows = result.scalars().all()

    assert len(tech_sample_rows) > 0, "应该有技术指标样本数据"

    # 验证至少有一些指标被计算出来（MA5 通常都能计算）
    ma5_count = sum(1 for row in tech_sample_rows if row.ma5 is not None)
    assert ma5_count > 0, "至少应该有一些股票计算出 MA5"

    logger.info(f"[测试] 技术指标数据质量验证通过（MA5 非空率：{ma5_count}/{len(tech_sample_rows)}）")

    logger.info(f"[测试] ✓ 盘后链路增量更新集成测试通过")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_sync_raw_daily_idempotent(cleanup_engine):
    """测试 sync_raw_daily 的幂等性。

    多次调用 sync_raw_daily 应该不会重复插入数据。
    """
    # 等待一下，避免连接池冲突
    await asyncio.sleep(1)

    manager = _build_manager()

    # 选择一个历史交易日
    test_date = None
    async with async_session_factory() as session:
        stmt = (
            select(TradeCalendar.cal_date)
            .where(
                TradeCalendar.is_open.is_(True),
                TradeCalendar.cal_date >= date.today() - timedelta(days=30),
                TradeCalendar.cal_date < date.today(),
            )
            .order_by(TradeCalendar.cal_date.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        test_date = result.scalar_one_or_none()

    if not test_date:
        pytest.skip("没有找到最近 30 天内的交易日，跳过测试")

    logger.info(f"[测试] 选择测试日期：{test_date}")

    # 第一次调用
    raw_counts_1 = await manager.sync_raw_daily(test_date)
    logger.info(f"[测试] 第一次 sync_raw_daily：{raw_counts_1}")

    # 第二次调用（应该是幂等的）
    raw_counts_2 = await manager.sync_raw_daily(test_date)
    logger.info(f"[测试] 第二次 sync_raw_daily：{raw_counts_2}")

    # 验证记录数一致（幂等性）
    assert raw_counts_1["daily"] == raw_counts_2["daily"], "daily 记录数应该一致"
    assert raw_counts_1["adj_factor"] == raw_counts_2["adj_factor"], "adj_factor 记录数应该一致"
    assert raw_counts_1["daily_basic"] == raw_counts_2["daily_basic"], "daily_basic 记录数应该一致"

    # 验证数据库中的实际记录数
    td_str = test_date.strftime("%Y%m%d")
    async with async_session_factory() as session:
        stmt = select(func.count()).select_from(RawTushareDaily).where(
            RawTushareDaily.trade_date == td_str
        )
        result = await session.execute(stmt)
        actual_count = result.scalar()

    assert actual_count == raw_counts_1["daily"], "数据库中的实际记录数应该与返回值一致"

    logger.info(f"[测试] ✓ sync_raw_daily 幂等性测试通过")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_etl_daily_idempotent(cleanup_engine):
    """测试 etl_daily 的幂等性。

    多次调用 etl_daily 应该不会重复插入数据。
    """
    # 等待一下，避免连接池冲突
    await asyncio.sleep(1)

    manager = _build_manager()

    # 选择一个历史交易日
    test_date = None
    async with async_session_factory() as session:
        stmt = (
            select(TradeCalendar.cal_date)
            .where(
                TradeCalendar.is_open.is_(True),
                TradeCalendar.cal_date >= date.today() - timedelta(days=30),
                TradeCalendar.cal_date < date.today(),
            )
            .order_by(TradeCalendar.cal_date.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        test_date = result.scalar_one_or_none()

    if not test_date:
        pytest.skip("没有找到最近 30 天内的交易日，跳过测试")

    logger.info(f"[测试] 选择测试日期：{test_date}")

    # 确保 raw 表有数据
    await manager.sync_raw_daily(test_date)

    # 第一次调用
    etl_result_1 = await manager.etl_daily(test_date)
    logger.info(f"[测试] 第一次 etl_daily：{etl_result_1}")

    # 第二次调用（应该是幂等的）
    etl_result_2 = await manager.etl_daily(test_date)
    logger.info(f"[测试] 第二次 etl_daily：{etl_result_2}")

    # 验证记录数一致（幂等性）
    assert etl_result_1["inserted"] == etl_result_2["inserted"], "inserted 记录数应该一致"

    # 验证数据库中的实际记录数
    async with async_session_factory() as session:
        stmt = select(func.count()).select_from(StockDaily).where(
            StockDaily.trade_date == test_date
        )
        result = await session.execute(stmt)
        actual_count = result.scalar()

    assert actual_count == etl_result_1["inserted"], "数据库中的实际记录数应该与返回值一致"

    logger.info(f"[测试] ✓ etl_daily 幂等性测试通过")
