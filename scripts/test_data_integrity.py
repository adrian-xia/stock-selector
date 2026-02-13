#!/usr/bin/env python3
"""测试数据完整性检查和断点续传功能。

测试场景：
1. 测试 detect_missing_dates() 方法
2. 测试启动时数据完整性检查
3. 测试 backfill-daily 命令
"""

import asyncio
import logging
from datetime import date, timedelta

from app.config import settings
from app.data.akshare import AKShareClient
from app.data.baostock import BaoStockClient
from app.data.manager import DataManager
from app.data.pool import get_pool
from app.database import async_session_factory
from app.logger import setup_logging
from app.scheduler.core import sync_from_progress

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


async def test_detect_missing_dates():
    """测试 detect_missing_dates() 方法。"""
    print("\n" + "=" * 60)
    print("测试 1: detect_missing_dates() 方法")
    print("=" * 60)

    manager = _build_manager()

    # 测试最近 7 天
    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    print(f"\n检查日期范围：{start_date} ~ {end_date}")

    missing_dates = await manager.detect_missing_dates(start_date, end_date)

    if missing_dates:
        print(f"✓ 发现 {len(missing_dates)} 个缺失交易日：")
        for d in missing_dates:
            print(f"  - {d}")
    else:
        print("✓ 数据完整，无缺失交易日")

    return missing_dates


async def test_startup_integrity_check():
    """测试启动时数据完整性检查。"""
    print("\n" + "=" * 60)
    print("测试 2: 启动时数据完整性检查")
    print("=" * 60)

    print(f"\n配置项：")
    print(f"  - DATA_INTEGRITY_CHECK_ENABLED: {settings.data_integrity_check_enabled}")
    print(f"  - DATA_INTEGRITY_CHECK_DAYS: {settings.data_integrity_check_days}")

    print("\n执行启动时检查（不跳过）...")
    await sync_from_progress(skip_check=False)
    print("✓ 启动时检查完成")

    print("\n执行启动时检查（跳过）...")
    await sync_from_progress(skip_check=True)
    print("✓ 跳过检查完成")


async def test_backfill_command():
    """测试 backfill-daily 命令（模拟）。"""
    print("\n" + "=" * 60)
    print("测试 3: backfill-daily 命令（模拟）")
    print("=" * 60)

    manager = _build_manager()

    # 测试最近 3 天
    end_date = date.today()
    start_date = end_date - timedelta(days=3)

    print(f"\n模拟补齐日期范围：{start_date} ~ {end_date}")

    # 1. 检测缺失日期
    missing_dates = await manager.detect_missing_dates(start_date, end_date)

    if not missing_dates:
        print("✓ 指定日期范围内数据完整，无需补齐")
        return

    print(f"✓ 发现 {len(missing_dates)} 个缺失交易日")

    # 2. 获取股票列表
    stocks = await manager.get_stock_list(status="L")
    print(f"✓ 共 {len(stocks)} 只上市股票")

    # 3. 模拟补齐（不实际执行，只显示会补齐哪些日期）
    print(f"\n将补齐以下日期：")
    for d in missing_dates:
        print(f"  - {d}")

    print("\n注意：这是模拟测试，未实际执行补齐操作")
    print("如需实际补齐，请运行：")
    print(f"  uv run python -m app.data.cli backfill-daily --start {start_date} --end {end_date}")


async def main():
    """主测试函数。"""
    setup_logging("INFO")

    print("\n" + "=" * 60)
    print("数据完整性检查和断点续传功能测试")
    print("=" * 60)

    try:
        # 测试 1: detect_missing_dates()
        missing_dates = await test_detect_missing_dates()

        # 测试 2: 启动时检查
        await test_startup_integrity_check()

        # 测试 3: backfill 命令
        await test_backfill_command()

        print("\n" + "=" * 60)
        print("所有测试完成")
        print("=" * 60)

        if missing_dates:
            print(f"\n⚠️  发现 {len(missing_dates)} 个缺失交易日")
            print("建议运行以下命令补齐数据：")
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            print(f"  uv run python -m app.data.cli backfill-daily --start {start_date} --end {end_date}")
        else:
            print("\n✓ 数据完整，无需补齐")

    except Exception as e:
        logger.error("测试失败：%s", e, exc_info=True)
        print(f"\n✗ 测试失败：{e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
