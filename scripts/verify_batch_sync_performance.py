#!/usr/bin/env python3
"""验证批量同步性能提升。

此脚本在真实环境中测试批量同步性能，对比优化前后的耗时。

运行前提：
1. 数据库已初始化（alembic upgrade head）
2. 股票列表已同步（python -m app.data.cli sync-stocks）
3. BaoStock API 可访问

运行方式：
    uv run python scripts/verify_batch_sync_performance.py

可选参数：
    --stock-count N    测试 N 只股票（默认 50）
    --date YYYY-MM-DD  测试日期（默认今天）
"""

import asyncio
import sys
import time
from datetime import date, datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.data.batch import batch_sync_daily
from app.data.baostock import BaoStockClient
from app.data.manager import DataManager
from app.data.pool import BaoStockConnectionPool, close_pool, get_pool
from app.database import async_session_factory


async def test_serial_sync(stock_codes: list[str], target_date: date) -> dict:
    """测试串行同步（旧方式）。"""
    print(f"\n{'='*60}")
    print("测试 1: 串行同步（旧方式）")
    print(f"{'='*60}")

    # 不使用连接池
    client = BaoStockClient()
    manager = DataManager(
        session_factory=async_session_factory,
        clients={"baostock": client},
        primary="baostock",
    )

    start = time.monotonic()
    success = 0
    failed = 0

    for i, code in enumerate(stock_codes, 1):
        try:
            await manager.sync_daily(code, target_date, target_date)
            success += 1
            if i % 10 == 0:
                print(f"  进度: {i}/{len(stock_codes)} ({i/len(stock_codes)*100:.1f}%)")
        except Exception as e:
            failed += 1
            print(f"  ⚠️  {code} 失败: {e}")

    elapsed = time.monotonic() - start

    result = {
        "method": "串行同步",
        "success": success,
        "failed": failed,
        "elapsed": elapsed,
    }

    print(f"\n结果:")
    print(f"  成功: {success} 只")
    print(f"  失败: {failed} 只")
    print(f"  耗时: {elapsed:.2f} 秒")
    print(f"  平均: {elapsed/len(stock_codes):.3f} 秒/只")

    return result


async def test_batch_sync(stock_codes: list[str], target_date: date) -> dict:
    """测试批量并发同步（新方式）。"""
    print(f"\n{'='*60}")
    print("测试 2: 批量并发同步（新方式）")
    print(f"{'='*60}")

    # 使用连接池
    pool = get_pool()

    start = time.monotonic()

    result = await batch_sync_daily(
        session_factory=async_session_factory,
        stock_codes=stock_codes,
        target_date=target_date,
        connection_pool=pool,
        batch_size=settings.daily_sync_batch_size,
        concurrency=settings.daily_sync_concurrency,
    )

    elapsed = time.monotonic() - start

    await close_pool()

    result_summary = {
        "method": "批量并发同步",
        "success": result["success"],
        "failed": result["failed"],
        "elapsed": elapsed,
    }

    print(f"\n结果:")
    print(f"  成功: {result['success']} 只")
    print(f"  失败: {result['failed']} 只")
    print(f"  耗时: {elapsed:.2f} 秒")
    print(f"  平均: {elapsed/len(stock_codes):.3f} 秒/只")

    return result_summary


async def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="验证批量同步性能提升")
    parser.add_argument("--stock-count", type=int, default=50, help="测试股票数量")
    parser.add_argument("--date", type=str, help="测试日期 (YYYY-MM-DD)")
    parser.add_argument("--skip-serial", action="store_true", help="跳过串行测试（节省时间）")
    args = parser.parse_args()

    # 解析日期
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = date.today()

    print(f"\n{'='*60}")
    print("批量同步性能验证")
    print(f"{'='*60}")
    print(f"测试日期: {target_date}")
    print(f"测试股票数: {args.stock_count}")
    print(f"批量大小: {settings.daily_sync_batch_size}")
    print(f"并发数: {settings.daily_sync_concurrency}")
    print(f"连接池大小: {settings.baostock_pool_size}")

    # 获取股票列表
    print(f"\n正在获取股票列表...")
    manager = DataManager(
        session_factory=async_session_factory,
        clients={"baostock": BaoStockClient()},
        primary="baostock",
    )
    stocks = await manager.get_stock_list(status="L")

    if len(stocks) < args.stock_count:
        print(f"⚠️  数据库中只有 {len(stocks)} 只股票，将使用全部")
        stock_codes = [s["ts_code"] for s in stocks]
    else:
        stock_codes = [s["ts_code"] for s in stocks[:args.stock_count]]

    print(f"✓ 获取到 {len(stock_codes)} 只股票")

    # 运行测试
    results = []

    if not args.skip_serial:
        result1 = await test_serial_sync(stock_codes, target_date)
        results.append(result1)
    else:
        print(f"\n跳过串行测试（使用 --skip-serial）")

    result2 = await test_batch_sync(stock_codes, target_date)
    results.append(result2)

    # 对比结果
    print(f"\n{'='*60}")
    print("性能对比")
    print(f"{'='*60}")

    if len(results) == 2:
        serial_time = results[0]["elapsed"]
        batch_time = results[1]["elapsed"]
        speedup = serial_time / batch_time if batch_time > 0 else 0

        print(f"\n串行同步: {serial_time:.2f} 秒")
        print(f"批量同步: {batch_time:.2f} 秒")
        print(f"性能提升: {speedup:.2f}x")
        print(f"节省时间: {serial_time - batch_time:.2f} 秒 ({(1-batch_time/serial_time)*100:.1f}%)")

        # 推算全量同步时间
        if len(stocks) > len(stock_codes):
            total_stocks = len(stocks)
            estimated_serial = serial_time * total_stocks / len(stock_codes)
            estimated_batch = batch_time * total_stocks / len(stock_codes)

            print(f"\n推算全量同步 {total_stocks} 只股票:")
            print(f"  串行方式: {estimated_serial/60:.1f} 分钟 ({estimated_serial/3600:.2f} 小时)")
            print(f"  批量方式: {estimated_batch/60:.1f} 分钟 ({estimated_batch/3600:.2f} 小时)")
            print(f"  节省时间: {(estimated_serial-estimated_batch)/60:.1f} 分钟")
    else:
        print(f"\n批量同步: {batch_time:.2f} 秒")
        print(f"平均: {batch_time/len(stock_codes):.3f} 秒/只")

        # 推算全量同步时间
        if len(stocks) > len(stock_codes):
            total_stocks = len(stocks)
            estimated_batch = batch_time * total_stocks / len(stock_codes)
            print(f"\n推算全量同步 {total_stocks} 只股票:")
            print(f"  预计耗时: {estimated_batch/60:.1f} 分钟 ({estimated_batch/3600:.2f} 小时)")

    print(f"\n{'='*60}")
    print("验证完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
