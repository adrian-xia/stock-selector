#!/usr/bin/env python3
"""数据初始化向导。

交互式引导用户完成首次数据初始化：
1. 检测数据库状态
2. 选择数据范围（1年/3年/自定义）
3. 执行初始化流程：股票列表 → 交易日历 → 日线数据 → 技术指标
"""

import asyncio
import logging
import sys
import time
from datetime import date, timedelta

from sqlalchemy import select, text

from app.config import settings
from app.data.indicator import compute_all_stocks
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.database import async_session_factory
from app.logger import setup_logging
from app.models.market import StockDaily

logger = logging.getLogger(__name__)


def _generate_quarter_periods(start_date: date, end_date: date) -> list[str]:
    """生成日期范围内所有季度末日期字符串列表。

    季度末 = 0331, 0630, 0930, 1231
    例：2024-01-01 ~ 2025-06-30 → ["20240331", "20240630", "20240930", "20241231", "20250331", "20250630"]
    """
    quarter_ends = [(3, 31), (6, 30), (9, 30), (12, 31)]
    periods: list[str] = []
    for year in range(start_date.year, end_date.year + 1):
        for month, day in quarter_ends:
            qe = date(year, month, day)
            if start_date <= qe <= end_date:
                periods.append(qe.strftime("%Y%m%d"))
    return periods


def _build_manager() -> DataManager:
    """构建 DataManager 实例。"""
    clients = {
        "tushare": TushareClient(
            token=settings.tushare_token,
            qps_limit=settings.tushare_qps_limit,
            retry_count=settings.tushare_retry_count,
            retry_interval=settings.tushare_retry_interval,
        ),
    }
    return DataManager(
        session_factory=async_session_factory,
        clients=clients,
        primary="tushare",
    )


async def check_database_status() -> dict:
    """检测数据库状态。

    Returns:
        dict: {
            "has_stocks": bool,  # 是否有股票列表数据
            "has_daily": bool,   # 是否有日线数据
            "daily_count": int,  # 日线数据记录数
            "stock_count": int,  # 股票数量
        }
    """
    async with async_session_factory() as session:
        # 检查股票列表
        stock_count_result = await session.execute(text("SELECT COUNT(*) FROM stocks"))
        stock_count = stock_count_result.scalar()

        # 检查日线数据
        daily_count_result = await session.execute(text("SELECT COUNT(*) FROM stock_daily"))
        daily_count = daily_count_result.scalar()

        return {
            "has_stocks": stock_count > 0,
            "has_daily": daily_count > 0,
            "daily_count": daily_count,
            "stock_count": stock_count,
        }


def get_user_choice() -> tuple[date, date]:
    """交互式获取用户选择的数据范围。

    Returns:
        tuple[date, date]: (start_date, end_date)
    """
    print("\n" + "=" * 60)
    print("请选择要初始化的数据范围：")
    print("=" * 60)
    print()
    print("1. 最近 1 年（约 250 个交易日，推荐用于快速测试）")
    print("2. 最近 3 年（约 750 个交易日，推荐用于日常使用）")
    print("3. 自定义范围（指定起止日期）")
    print()

    while True:
        choice = input("请输入选项 (1/2/3): ").strip()

        end_date = date.today()

        if choice == "1":
            # 1 年 ≈ 250 交易日 ≈ 365 天
            start_date = end_date - timedelta(days=365)
            print(f"\n✓ 已选择：最近 1 年（{start_date} ~ {end_date}）")
            return start_date, end_date

        elif choice == "2":
            # 3 年 ≈ 750 交易日 ≈ 1095 天
            start_date = end_date - timedelta(days=1095)
            print(f"\n✓ 已选择：最近 3 年（{start_date} ~ {end_date}）")
            return start_date, end_date

        elif choice == "3":
            print()
            start_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
            end_str = input("请输入结束日期 (YYYY-MM-DD，留空则使用今天): ").strip()

            try:
                start_date = date.fromisoformat(start_str)
                end_date = date.fromisoformat(end_str) if end_str else date.today()

                # 验证日期范围
                if start_date >= end_date:
                    print("✗ 错误：开始日期必须早于结束日期")
                    continue

                # 计算年数
                days_diff = (end_date - start_date).days
                years = days_diff / 365

                # 大数据范围警告
                if years > 5:
                    print()
                    print("⚠️  警告：您选择了超过 5 年的数据范围")
                    print(f"   数据量：约 {int(years * 250)} 个交易日")
                    print("   预计耗时：数小时（取决于网络速度和 API 限流）")
                    print()
                    confirm = input("是否继续？(y/n): ").strip().lower()
                    if confirm != "y":
                        print("已取消")
                        continue

                print(f"\n✓ 已选择：自定义范围（{start_date} ~ {end_date}）")
                return start_date, end_date

            except ValueError as e:
                print(f"✗ 日期格式错误：{e}")
                continue

        else:
            print("✗ 无效选项，请输入 1、2 或 3")


async def sync_stock_list(manager: DataManager) -> int:
    """步骤 1：同步股票列表。

    Returns:
        int: 同步的股票数量
    """
    print("\n" + "=" * 60)
    print("步骤 1/4: 同步股票列表")
    print("=" * 60)

    result = await manager.sync_stock_list()
    stock_count = result.get("total", 0)

    print(f"✓ 股票列表同步完成：共 {stock_count} 只股票")
    return stock_count


async def sync_trade_calendar(manager: DataManager, start_date: date, end_date: date) -> int:
    """步骤 2：同步交易日历。

    Returns:
        int: 同步的交易日数量
    """
    print("\n" + "=" * 60)
    print("步骤 2/4: 同步交易日历")
    print("=" * 60)
    print(f"日期范围：{start_date} ~ {end_date}")

    result = await manager.sync_trade_calendar(start_date, end_date)
    calendar_count = result.get("total", 0)

    print(f"✓ 交易日历同步完成：共 {calendar_count} 个交易日")
    return calendar_count


async def sync_daily_data(
    manager: DataManager,
    start_date: date,
    end_date: date,
    stock_count: int,
) -> dict:
    """步骤 3：通过统一入口同步所有 raw 表 + ETL。

    Returns:
        dict: 各组同步结果
    """
    print("\n" + "=" * 60)
    print("步骤 3/4: 同步全量数据（raw-first）")
    print("=" * 60)
    print(f"日期范围：{start_date} ~ {end_date}")
    print()

    overall_start = time.monotonic()
    results = {}

    # P0: 日线数据（按交易日逐日同步，显示进度）
    print("⏳ [P0] 同步日线数据...")
    trading_dates = await manager.get_trade_calendar(start_date, end_date)
    if trading_dates:
        p0_success, p0_failed = 0, 0
        for i, trade_date in enumerate(trading_dates, 1):
            try:
                await manager.sync_raw_daily(trade_date)
                await manager.etl_daily(trade_date)
                p0_success += 1
            except Exception as e:
                logger.error("P0 日期 %s 失败：%s", trade_date, e)
                p0_failed += 1
            if i % 10 == 0 or i == len(trading_dates):
                print(f"   [init] P0 日线 [{i}/{len(trading_dates)}] {trade_date} ✓")
        results["p0"] = {"success": p0_success, "failed": p0_failed}
        print(f"✓ [P0] 完成：成功 {p0_success} 天，失败 {p0_failed} 天")
    else:
        print("✗ [P0] 无交易日数据")

    # P1: 财务数据（按季度同步）
    print("\n⏳ [P1] 同步财务数据...")
    try:
        periods = _generate_quarter_periods(start_date, end_date)
        p1_success, p1_failed = 0, 0
        for i, period in enumerate(periods, 1):
            try:
                await manager.sync_raw_fina(period)
                await manager.etl_fina(period)
                p1_success += 1
            except Exception as e:
                logger.error("P1 季度 %s 失败：%s", period, e)
                p1_failed += 1
            if i % 4 == 0 or i == len(periods):
                print(f"   [init] P1 财务 [{i}/{len(periods)}] {period} ✓")
        results["p1"] = {"success": p1_success, "failed": p1_failed}
        print(f"✓ [P1] 完成：成功 {p1_success} 季，失败 {p1_failed} 季")
    except Exception as e:
        print(f"✗ [P1] 失败：{e}")

    # P2: 资金流向
    print("\n⏳ [P2] 同步资金流向...")
    try:
        p2_result = await manager.sync_raw_tables("p2", start_date, end_date, mode="full")
        results["p2"] = p2_result
        print(f"✓ [P2] 完成")
    except Exception as e:
        print(f"✗ [P2] 失败：{e}")

    # P3: 指数数据
    print("\n⏳ [P3] 同步指数数据...")
    try:
        p3d_result = await manager.sync_raw_tables("p3_daily", start_date, end_date, mode="full")
        p3s_result = await manager.sync_raw_tables("p3_static", start_date, end_date, mode="full")
        results["p3"] = {"daily": p3d_result, "static": p3s_result}
        print(f"✓ [P3] 完成")
    except Exception as e:
        print(f"✗ [P3] 失败：{e}")

    # P4: 板块数据
    print("\n⏳ [P4] 同步板块数据...")
    try:
        # 板块基础信息
        print("   同步板块列表...")
        await manager.sync_concept_index(src="THS")

        # 板块日线（逐日）
        print("   同步板块日线...")
        for i, td in enumerate(trading_dates, 1):
            td_str = td.strftime("%Y%m%d")
            await manager.sync_concept_daily(trade_date=td_str)
            if i % 10 == 0 or i == len(trading_dates):
                print(f"   [init] P4 板块日线 [{i}/{len(trading_dates)}] {td_str} ✓")

        # 板块成分股
        print("   同步板块成分股...")
        from sqlalchemy import select as sa_select
        from app.models.concept import ConceptIndex
        async with async_session_factory() as session:
            result = await session.execute(sa_select(ConceptIndex.ts_code))
            concept_codes = [r[0] for r in result.all()]
        for i, code in enumerate(concept_codes, 1):
            try:
                await manager.sync_concept_member(code, src="THS")
            except Exception as e:
                logger.error("板块 %s 成分股同步失败：%s", code, e)
            if i % 50 == 0 or i == len(concept_codes):
                print(f"   [init] P4 成分股 [{i}/{len(concept_codes)}] {code} ✓")

        results["p4"] = {"status": "ok"}
        print("✓ [P4] 完成")
    except Exception as e:
        print(f"✗ [P4] 失败：{e}")

    # P5: 扩展数据
    print("\n⏳ [P5] 同步扩展数据...")
    try:
        p5_result = await manager.sync_raw_tables("p5", start_date, end_date, mode="full")
        results["p5"] = p5_result
        print(f"✓ [P5] 完成")
    except Exception as e:
        print(f"✗ [P5] 失败：{e}")

    overall_elapsed = int(time.monotonic() - overall_start)
    print(f"\n✓ 全量数据同步完成，耗时 {overall_elapsed // 60}分{overall_elapsed % 60}秒")
    return results


async def compute_indicators() -> dict:
    """步骤 4：计算技术指标。

    Returns:
        dict: {"total": int, "success": int, "failed": int}
    """
    print("\n" + "=" * 60)
    print("步骤 4/4: 计算技术指标")
    print("=" * 60)
    print()
    print("⏳ 正在计算技术指标（MA/MACD/KDJ/RSI/BOLL/ATR）...")
    print()

    def progress_callback(processed: int, total: int) -> None:
        """进度回调：每 500 只股票打印一次。"""
        if processed % 500 == 0 or processed == total:
            progress = (processed / total) * 100
            print(f"[{processed}/{total}] {progress:.1f}% - 正在计算技术指标...")

    result = await compute_all_stocks(
        async_session_factory,
        progress_callback=progress_callback,
    )

    print()
    print(f"✓ 技术指标计算完成：")
    print(f"   总计：{result['total']} 只")
    print(f"   成功：{result['success']} 只")
    print(f"   失败：{result['failed']} 只")
    print(f"   耗时：{result['elapsed_seconds']}秒")

    return result


async def main():
    """主函数。"""
    setup_logging("INFO")

    print("\n" + "=" * 60)
    print("A 股智能选股系统 - 数据初始化向导")
    print("=" * 60)

    # 1. 检测数据库状态
    print("\n正在检测数据库状态...")
    status = await check_database_status()

    if status["has_daily"]:
        print()
        print("⚠️  数据库已有数据：")
        print(f"   股票数量：{status['stock_count']} 只")
        print(f"   日线记录：{status['daily_count']} 条")
        print()
        confirm = input("是否继续初始化（会追加新数据）？(y/n): ").strip().lower()
        if confirm != "y":
            print("\n已取消初始化")
            return 0

    # 2. 获取用户选择的数据范围
    start_date, end_date = get_user_choice()

    # 3. 确认开始
    print()
    print("=" * 60)
    print("初始化配置确认")
    print("=" * 60)
    print(f"数据范围：{start_date} ~ {end_date}")
    print(f"预计交易日：约 {int((end_date - start_date).days / 365 * 250)} 个")
    print()
    print("初始化流程：")
    print("  1. 同步股票列表（raw-first）")
    print("  2. 同步交易日历（raw-first）")
    print("  3. 同步全量数据（P0 日线 + P1 财务 + P2 资金 + P3 指数 + P4 板块 + P5 扩展）")
    print("  4. 计算技术指标")
    print()
    confirm = input("确认开始初始化？(y/n): ").strip().lower()
    if confirm != "y":
        print("\n已取消初始化")
        return 0

    # 4. 执行初始化流程
    overall_start = time.monotonic()
    manager = _build_manager()

    try:
        # 步骤 1: 同步股票列表
        stock_count = await sync_stock_list(manager)

        # 步骤 2: 同步交易日历
        calendar_count = await sync_trade_calendar(manager, start_date, end_date)

        # 步骤 3: 同步日线数据
        daily_result = await sync_daily_data(manager, start_date, end_date, stock_count)

        # 步骤 4: 计算技术指标
        indicator_result = await compute_indicators()

        # 5. 显示总结
        overall_elapsed = int(time.monotonic() - overall_start)
        overall_minutes = overall_elapsed // 60
        overall_seconds = overall_elapsed % 60

        print("\n" + "=" * 60)
        print("初始化完成")
        print("=" * 60)
        print(f"股票列表：{stock_count} 只")
        print(f"交易日历：{calendar_count} 个交易日")
        print(f"数据同步：P0/P1/P2/P3/P4/P5 全量完成")
        print(f"技术指标：成功 {indicator_result['success']} 只，失败 {indicator_result['failed']} 只")
        print(f"总耗时：{overall_minutes}分{overall_seconds}秒")
        print()
        print("✓ 数据初始化完成，可以启动服务了：")
        print("  uv run uvicorn app.main:app --reload")
        print()

        return 0

    except Exception as e:
        logger.error("初始化失败：%s", e, exc_info=True)
        print(f"\n✗ 初始化失败：{e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
