"""验证策略引擎和回测引擎（1 年数据范围）。

本脚本用于验证 Tushare 迁移后，策略引擎和回测引擎能否正常工作。
使用 1 年的数据范围进行测试。
"""

import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtest.engine import run_backtest
from app.config import settings
from app.database import async_session_factory
from app.logger import setup_logging
from app.strategy.pipeline import execute_pipeline
from sqlalchemy import select, text

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)


async def verify_data_availability(start_date: date, end_date: date) -> bool:
    """验证数据库中是否有指定日期范围的数据。"""
    logger.info(f"检查数据可用性：{start_date} 到 {end_date}")

    async with async_session_factory() as session:
        # 检查股票列表
        result = await session.execute(text("SELECT COUNT(*) FROM stocks WHERE list_status = 'L'"))
        stock_count = result.scalar()
        logger.info(f"  - 上市股票数量：{stock_count}")

        if stock_count == 0:
            logger.error("❌ 没有上市股票数据")
            return False

        # 检查交易日历
        result = await session.execute(
            text("SELECT COUNT(*) FROM trade_calendar WHERE cal_date BETWEEN :start AND :end AND is_open = true"),
            {"start": start_date, "end": end_date}
        )
        trade_days = result.scalar()
        logger.info(f"  - 交易日数量：{trade_days}")

        if trade_days == 0:
            logger.error("❌ 没有交易日数据")
            return False

        # 获取所有交易日
        result = await session.execute(
            text("SELECT cal_date FROM trade_calendar WHERE cal_date BETWEEN :start AND :end AND is_open = true ORDER BY cal_date"),
            {"start": start_date, "end": end_date}
        )
        trade_dates = [row[0] for row in result.fetchall()]

        # 检查日线数据 - 逐日检查数据量
        result = await session.execute(
            text("SELECT trade_date, COUNT(*) as cnt FROM stock_daily WHERE trade_date BETWEEN :start AND :end GROUP BY trade_date"),
            {"start": start_date, "end": end_date}
        )
        daily_counts = {row[0]: row[1] for row in result.fetchall()}

        missing_dates = []
        low_count_dates = []
        min_expected_count = stock_count * 0.5  # 至少应该有 50% 的股票有数据

        for trade_date in trade_dates:
            count = daily_counts.get(trade_date, 0)
            if count == 0:
                missing_dates.append(trade_date)
            elif count < min_expected_count:
                low_count_dates.append((trade_date, count))

        if missing_dates:
            logger.error(f"❌ 发现 {len(missing_dates)} 个交易日完全没有日线数据：")
            for missing_date in missing_dates[:5]:
                logger.error(f"    - {missing_date}")
            if len(missing_dates) > 5:
                logger.error(f"    ... 还有 {len(missing_dates) - 5} 个")
            return False

        if low_count_dates:
            logger.error(f"❌ 发现 {len(low_count_dates)} 个交易日数据量异常（< {min_expected_count:.0f} 条）：")
            for trade_date, count in low_count_dates[:5]:
                logger.error(f"    - {trade_date}：{count} 条（预期 {stock_count} 条）")
            if len(low_count_dates) > 5:
                logger.error(f"    ... 还有 {len(low_count_dates) - 5} 个")
            return False

        logger.info(f"  - 有日线数据的日期数：{len(daily_counts)}")

        # 检查技术指标
        result = await session.execute(
            text("SELECT COUNT(DISTINCT trade_date) FROM technical_daily WHERE trade_date BETWEEN :start AND :end"),
            {"start": start_date, "end": end_date}
        )
        tech_days = result.scalar()
        logger.info(f"  - 有技术指标的日期数：{tech_days}")

        if tech_days == 0:
            logger.error("❌ 没有技术指标数据")
            return False

        logger.info("✅ 数据可用性检查通过")
        return True


async def verify_strategy_engine(target_date: date) -> bool:
    """验证策略引擎。"""
    logger.info(f"\n{'='*60}")
    logger.info(f"验证策略引擎（目标日期：{target_date}）")
    logger.info(f"{'='*60}")

    try:
        # 执行策略管道（使用 ma-cross 策略）
        result = await execute_pipeline(
            session_factory=async_session_factory,
            strategy_names=["ma-cross"],
            target_date=target_date,
            top_n=10,
        )

        logger.info(f"  - 目标日期：{result.target_date}")
        logger.info(f"  - 选股数量：{len(result.picks)}")
        logger.info(f"  - 耗时：{result.elapsed_ms} ms")
        logger.info(f"  - 层级统计：{result.layer_stats}")

        if len(result.picks) > 0:
            logger.info(f"  - 前 3 只股票：")
            for pick in result.picks[:3]:
                logger.info(f"    - {pick.ts_code} {pick.name}: {pick.close:.2f} ({pick.pct_chg:+.2f}%)")

        if len(result.picks) == 0:
            logger.warning("⚠️  策略引擎运行成功，但未选出股票（可能是正常情况）")
            return True

        logger.info("✅ 策略引擎验证通过")
        return True

    except Exception as e:
        logger.error(f"❌ 策略引擎验证失败：{e}", exc_info=True)
        return False


async def verify_backtest_engine(start_date: date, end_date: date) -> bool:
    """验证回测引擎。"""
    logger.info(f"\n{'='*60}")
    logger.info(f"验证回测引擎（{start_date} 到 {end_date}）")
    logger.info(f"{'='*60}")

    try:
        # 选择几只流动性好的股票进行回测
        test_stocks = ["600519.SH", "000858.SZ", "601318.SH"]  # 茅台、五粮液、平安

        logger.info(f"  - 测试股票：{test_stocks}")
        logger.info(f"  - 初始资金：1,000,000")

        # 执行回测
        result = await run_backtest(
            session_factory=async_session_factory,
            strategy_name="ma-cross",
            strategy_params={},  # 使用默认参数
            stock_codes=test_stocks,
            start_date=start_date,
            end_date=end_date,
            initial_capital=1_000_000,
        )

        # 从 strategy_instance 获取回测指标
        strat = result["strategy_instance"]
        logger.info(f"  - 最终市值：{strat.broker.getvalue():,.2f}")
        logger.info(f"  - 总收益率：{(strat.broker.getvalue() / 1_000_000 - 1) * 100:.2f}%")
        logger.info(f"  - 交易次数：{len(result['trades_log'])}")
        logger.info(f"  - 耗时：{result['elapsed_ms']} ms")

        logger.info("✅ 回测引擎验证通过")
        return True

    except Exception as e:
        logger.error(f"❌ 回测引擎验证失败：{e}", exc_info=True)
        return False


async def main():
    """主函数。"""
    logger.info("="*60)
    logger.info("开始验证策略引擎和回测引擎（1 年数据范围）")
    logger.info("="*60)

    # 计算日期范围（最近 1 年）
    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    logger.info(f"数据范围：{start_date} 到 {end_date}")

    # 1. 验证数据可用性
    if not await verify_data_availability(start_date, end_date):
        logger.error("\n❌ 数据可用性检查失败，无法继续验证")
        sys.exit(1)

    # 2. 验证策略引擎（使用最近的交易日）
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT cal_date FROM trade_calendar WHERE cal_date <= :end AND is_open = true ORDER BY cal_date DESC LIMIT 1"),
            {"end": end_date}
        )
        latest_trade_date = result.scalar()

    if not latest_trade_date:
        logger.error("❌ 找不到最近的交易日")
        sys.exit(1)

    strategy_ok = await verify_strategy_engine(latest_trade_date)

    # 3. 验证回测引擎（使用 1 年数据）
    backtest_ok = await verify_backtest_engine(start_date, end_date)

    # 总结
    logger.info(f"\n{'='*60}")
    logger.info("验证结果总结")
    logger.info(f"{'='*60}")
    logger.info(f"  - 数据可用性：✅")
    logger.info(f"  - 策略引擎：{'✅' if strategy_ok else '❌'}")
    logger.info(f"  - 回测引擎：{'✅' if backtest_ok else '❌'}")

    if strategy_ok and backtest_ok:
        logger.info("\n🎉 所有验证通过！")
        sys.exit(0)
    else:
        logger.error("\n❌ 部分验证失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
