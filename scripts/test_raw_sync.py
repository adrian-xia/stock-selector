"""测试 raw 数据全量同步：逐组测试 P0-P5，验证数据是否可以落库。"""

import asyncio
import logging
import time
from datetime import date

from app.config import settings
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.database import async_session_factory
from app.logger import setup_logging

setup_logging("INFO")
logger = logging.getLogger(__name__)


def _build_manager() -> DataManager:
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


async def check_raw_tables():
    """检查所有 raw 表的数据量。"""
    from sqlalchemy import text
    async with async_session_factory() as session:
        # 获取所有 raw_ 开头的表
        result = await session.execute(text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename LIKE 'raw_%' "
            "ORDER BY tablename"
        ))
        tables = [r[0] for r in result.all()]

        print(f"\n{'='*70}")
        print(f"{'表名':<45} {'行数':>10}")
        print(f"{'='*70}")

        total_rows = 0
        empty_tables = []
        for table in tables:
            count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            count = count_result.scalar()
            total_rows += count
            status = "" if count > 0 else " ⚠️ 空"
            print(f"{table:<45} {count:>10,}{status}")
            if count == 0:
                empty_tables.append(table)

        print(f"{'='*70}")
        print(f"{'总计':<45} {total_rows:>10,}")
        print(f"\n共 {len(tables)} 张 raw 表，{len(tables) - len(empty_tables)} 张有数据，{len(empty_tables)} 张为空")
        if empty_tables:
            print(f"\n空表列表：")
            for t in empty_tables:
                print(f"  - {t}")
        return empty_tables


async def test_incremental_sync(target: date):
    """测试增量同步（单日）。"""
    manager = _build_manager()

    print(f"\n{'='*70}")
    print(f"测试增量同步：target_date={target}")
    print(f"{'='*70}")

    groups = ["p0", "p2", "p3_daily", "p3_static", "p5"]
    for group in groups:
        start = time.monotonic()
        print(f"\n--- 同步 {group} ---")
        try:
            result = await manager.sync_raw_tables(group, target, target, mode="incremental")
            elapsed = time.monotonic() - start
            if result:
                ok = sum(1 for v in result.values() if isinstance(v, dict) and v.get("error") is None)
                fail = sum(1 for v in result.values() if isinstance(v, dict) and v.get("error"))
                rows = sum(v.get("rows", 0) for v in result.values() if isinstance(v, dict))
                print(f"  ✓ 完成：{ok} 成功，{fail} 失败，{rows} 行，耗时 {elapsed:.1f}s")
                # 显示失败详情
                for table, info in result.items():
                    if isinstance(info, dict) and info.get("error"):
                        print(f"    ✗ {table}: {info['error'][:100]}")
            else:
                print(f"  ✓ 完成（无结果），耗时 {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.monotonic() - start
            print(f"  ✗ 失败：{e}，耗时 {elapsed:.1f}s")


async def main():
    # 先查询最近交易日
    from sqlalchemy import text
    async with async_session_factory() as session:
        result = await session.execute(text(
            "SELECT cal_date FROM trade_calendar "
            "WHERE is_open = true AND cal_date <= CURRENT_DATE "
            "ORDER BY cal_date DESC LIMIT 1"
        ))
        latest = result.scalar()

    if latest is None:
        print("❌ 交易日历为空，请先同步交易日历")
        return

    print(f"最近交易日：{latest}")

    # 1. 先看当前 raw 表状态
    print("\n📊 当前 raw 表状态：")
    await check_raw_tables()

    # 2. 测试增量同步
    await test_incremental_sync(latest)

    # 3. 同步后再看状态
    print("\n📊 同步后 raw 表状态：")
    await check_raw_tables()


if __name__ == "__main__":
    asyncio.run(main())
