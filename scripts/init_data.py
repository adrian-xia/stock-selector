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
from app.data.akshare import AKShareClient
from app.data.baostock import BaoStockClient
from app.data.batch import batch_sync_daily
from app.data.indicator import compute_all_stocks
from app.data.manager import DataManager
from app.data.pool import get_pool
from app.database import async_session_factory
from app.logger import setup_logging
from app.models.stock import StockDaily

logger = logging.getLogger(__name__)


def _build_manager() -> DataManager:
    """构建 DataManager 实例。"""
    pool = get_pool()
    clients = {
        "baostock": BaoStockClient(connection_pool=pool),
        "akshare": AKShareClient(),
    }
    return DataManager(
        session_factory=async_session_factory,
        clients=clients,
        primary="baostock",
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
    """步骤 3：同步日线数据。

    Returns:
        dict: {"success": int, "failed": int}
    """
    print("\n" + "=" * 60)
    print("步骤 3/4: 同步日线数据")
    print("=" * 60)
    print(f"日期范围：{start_date} ~ {end_date}")
    print(f"股票数量：{stock_count} 只")
    print()
    print("⏳ 正在同步日线数据，请耐心等待...")
    print("   （根据数据范围和网络速度，可能需要数分钟到数小时）")
    print()

    # 获取所有上市股票
    stocks = await manager.get_stock_list(status="L")
    stock_codes = [s["ts_code"] for s in stocks]

    # 获取交易日列表
    trading_dates = await manager.get_trade_calendar(start_date, end_date)

    if not trading_dates:
        print("✗ 错误：指定日期范围内无交易日")
        return {"success": 0, "failed": 0}

    print(f"共需同步 {len(trading_dates)} 个交易日")
    print()

    # 逐个交易日同步
    pool = get_pool()
    total_success = 0
    total_failed = 0
    overall_start = time.monotonic()

    for i, trade_date in enumerate(trading_dates, 1):
        date_start = time.monotonic()

        try:
            result = await batch_sync_daily(
                session_factory=async_session_factory,
                stock_codes=stock_codes,
                target_date=trade_date,
                connection_pool=pool,
            )

            date_elapsed = time.monotonic() - date_start
            total_success += result["success"]
            total_failed += result["failed"]

            # 每 10 个交易日显示一次进度
            if i % 10 == 0 or i == len(trading_dates):
                progress = (i / len(trading_dates)) * 100
                print(f"[{i}/{len(trading_dates)}] {progress:.1f}% - "
                      f"最新日期：{trade_date}，"
                      f"成功 {result['success']} 只，失败 {result['failed']} 只，"
                      f"耗时 {int(date_elapsed)}秒")

                # 估算剩余时间
                if i < len(trading_dates):
                    avg_time = (time.monotonic() - overall_start) / i
                    remaining_time = int(avg_time * (len(trading_dates) - i))
                    remaining_minutes = remaining_time // 60
                    remaining_seconds = remaining_time % 60
                    print(f"   预计剩余时间：{remaining_minutes}分{remaining_seconds}秒")

        except Exception as e:
            logger.error("同步日期 %s 失败：%s", trade_date, e)
            print(f"✗ 日期 {trade_date} 同步失败：{e}")

    overall_elapsed = int(time.monotonic() - overall_start)
    overall_minutes = overall_elapsed // 60
    overall_seconds = overall_elapsed % 60

    print()
    print(f"✓ 日线数据同步完成：")
    print(f"   成功：{total_success} 只次")
    print(f"   失败：{total_failed} 只次")
    print(f"   总耗时：{overall_minutes}分{overall_seconds}秒")

    return {"success": total_success, "failed": total_failed}


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
    print("  1. 同步股票列表")
    print("  2. 同步交易日历")
    print("  3. 同步日线数据（耗时较长）")
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
        print(f"日线数据：成功 {daily_result['success']} 只次，失败 {daily_result['failed']} 只次")
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
