#!/usr/bin/env python3
"""快速验证批量同步功能。

此脚本快速测试批量同步是否正常工作，不进行性能对比。

运行方式：
    uv run python scripts/quick_verify_batch_sync.py
"""

import asyncio
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.data.batch import batch_sync_daily
from app.data.baostock import BaoStockClient
from app.data.manager import DataManager
from app.data.pool import close_pool, get_pool
from app.database import async_session_factory


async def main():
    """快速验证批量同步。"""
    print("\n" + "="*60)
    print("快速验证批量同步功能")
    print("="*60)

    # 配置
    test_count = 10  # 测试 10 只股票
    target_date = date.today()

    print(f"\n配置:")
    print(f"  测试日期: {target_date}")
    print(f"  测试股票数: {test_count}")
    print(f"  批量大小: {settings.daily_sync_batch_size}")
    print(f"  并发数: {settings.daily_sync_concurrency}")
    print(f"  连接池大小: {settings.baostock_pool_size}")

    # 获取股票列表
    print(f"\n[1/3] 获取股票列表...")
    manager = DataManager(
        session_factory=async_session_factory,
        clients={"baostock": BaoStockClient()},
        primary="baostock",
    )
    stocks = await manager.get_stock_list(status="L")
    stock_codes = [s["ts_code"] for s in stocks[:test_count]]
    print(f"  ✓ 获取到 {len(stock_codes)} 只股票: {', '.join(stock_codes[:5])}...")

    # 测试批量同步
    print(f"\n[2/3] 运行批量同步...")
    pool = get_pool()
    start = time.monotonic()

    try:
        result = await batch_sync_daily(
            session_factory=async_session_factory,
            stock_codes=stock_codes,
            target_date=target_date,
            connection_pool=pool,
            batch_size=settings.daily_sync_batch_size,
            concurrency=settings.daily_sync_concurrency,
        )
        elapsed = time.monotonic() - start

        print(f"\n[3/3] 结果:")
        print(f"  ✓ 成功: {result['success']} 只")
        if result['failed'] > 0:
            print(f"  ⚠️  失败: {result['failed']} 只")
            print(f"  失败股票: {', '.join(result['failed_codes'])}")
        print(f"  ⏱️  耗时: {elapsed:.2f} 秒")
        print(f"  📊 平均: {elapsed/len(stock_codes):.3f} 秒/只")

        # 推算全量同步时间
        if len(stocks) > test_count:
            total_stocks = len(stocks)
            estimated = elapsed * total_stocks / test_count
            print(f"\n推算全量同步 {total_stocks} 只股票:")
            print(f"  预计耗时: {estimated/60:.1f} 分钟 ({estimated/3600:.2f} 小时)")

        print(f"\n{'='*60}")
        if result['success'] == len(stock_codes):
            print("✅ 批量同步功能正常")
        else:
            print("⚠️  批量同步部分失败，请检查日志")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ 批量同步失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
