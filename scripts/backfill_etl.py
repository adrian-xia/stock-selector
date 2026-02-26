#!/usr/bin/env python3
"""补跑脚本：修复缺失的 ETL 数据和 P3 静态数据。

可与正在运行的 init-tushare 进程并行执行，互不冲突。

用法：
    APP_ENV_FILE=.env.prod uv run python -m scripts.backfill_etl [--step STEP]

步骤：
    1. p3_static  — 重跑 P3 行业分类(SW+SW2021) + 行业成分股(按L1逐个) + etl_index_static
    2. p2_etl     — 逐日 ETL：raw_moneyflow/top_list → money_flow/dragon_tiger
    3. p3_etl     — 逐日 ETL：raw_index_daily/weight/factor_pro → 业务表
    4. p5_etl     — 逐日 ETL：raw_suspend_d → suspend_info, raw_limit_list_d → limit_list_daily
    all           — 按顺序执行全部步骤
"""

import asyncio
import logging
import sys
import time
from datetime import date

from app.config import settings
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.database import async_session_factory
from app.logger import setup_logging

logger = logging.getLogger(__name__)

sys.path.insert(0, ".")


def _build_manager() -> DataManager:
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


async def step_p3_static(manager: DataManager) -> None:
    """步骤 1：重跑 P3 静态数据（行业分类 + 成分股 + ETL）。"""
    print("\n⏳ [步骤1] P3 静态数据：行业分类 + 成分股 + ETL")
    t0 = time.monotonic()

    # 行业分类（SW + SW2021）
    print("   同步行业分类...")
    r = await manager.sync_raw_industry_classify()
    print(f"   行业分类: {r.get('index_classify', 0)} 条")

    # 行业成分股（按 L1 逐个获取）
    print("   同步行业成分股...")
    r = await manager.sync_raw_industry_member()
    print(f"   行业成分股: {r.get('index_member_all', 0)} 条")

    # ETL：写入业务表
    print("   执行 etl_index_static...")
    r = await manager.etl_index_static()
    print(f"   ETL 结果: index_basic={r.get('index_basic', 0)}, "
          f"industry_classify={r.get('industry_classify', 0)}, "
          f"industry_member={r.get('industry_member', 0)}")

    print(f"✓ [步骤1] 完成，耗时 {time.monotonic() - t0:.1f}s")


async def step_p2_etl(manager: DataManager, start_date: date, end_date: date) -> None:
    """步骤 2：P2 ETL — 逐日清洗资金流向和龙虎榜到业务表。"""
    print("\n⏳ [步骤2] P2 ETL：资金流向 + 龙虎榜")
    t0 = time.monotonic()

    trading_dates = await manager.get_trade_calendar(start_date, end_date)
    total = len(trading_dates)
    print(f"   交易日数: {total}")

    ok, fail = 0, 0
    for i, td in enumerate(trading_dates, 1):
        try:
            r = await manager.etl_moneyflow(td)
            ok += 1
            if i % 100 == 0 or i == total:
                mf = r.get("money_flow", 0)
                dt = r.get("dragon_tiger", 0)
                print(f"   [{i}/{total}] {td} ✓ money_flow={mf}, dragon_tiger={dt}")
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"   [{i}/{total}] {td} ✗ {e}")

    print(f"✓ [步骤2] 完成：{ok} 成功，{fail} 失败，耗时 {time.monotonic() - t0:.1f}s")

async def step_p3_etl(manager: DataManager, start_date: date, end_date: date) -> None:
    """步骤 3：P3 ETL — 逐日清洗指数日线/权重/技术因子到业务表。"""
    print("\n⏳ [步骤3] P3 ETL：指数日线 + 权重 + 技术因子")
    t0 = time.monotonic()

    trading_dates = await manager.get_trade_calendar(start_date, end_date)
    total = len(trading_dates)
    print(f"   交易日数: {total}")

    ok, fail = 0, 0
    for i, td in enumerate(trading_dates, 1):
        try:
            r = await manager.etl_index(td)
            ok += 1
            if i % 100 == 0 or i == total:
                print(f"   [{i}/{total}] {td} ✓ "
                      f"index_daily={r.get('index_daily', 0)}, "
                      f"index_weight={r.get('index_weight', 0)}, "
                      f"index_technical={r.get('index_technical_daily', 0)}")
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"   [{i}/{total}] {td} ✗ {e}")

    print(f"✓ [步骤3] 完成：{ok} 成功，{fail} 失败，耗时 {time.monotonic() - t0:.1f}s")


async def step_p5_etl(manager: DataManager, start_date: date, end_date: date) -> None:
    """步骤 4：P5 ETL — 逐日清洗停复牌和涨跌停到业务表。"""
    print("\n⏳ [步骤4] P5 ETL：停复牌 + 涨跌停")
    t0 = time.monotonic()

    # 先检查 raw 表是否有数据
    from sqlalchemy import text
    async with async_session_factory() as session:
        r1 = await session.execute(text("SELECT COUNT(*) FROM raw_tushare_suspend_d"))
        r2 = await session.execute(text("SELECT COUNT(*) FROM raw_tushare_limit_list_d"))
        suspend_count = r1.scalar()
        limit_count = r2.scalar()

    if suspend_count == 0 and limit_count == 0:
        print("   ⚠ raw 表无数据（P5 同步可能尚未完成），跳过")
        return

    print(f"   raw 数据: suspend_d={suspend_count:,}, limit_list_d={limit_count:,}")

    trading_dates = await manager.get_trade_calendar(start_date, end_date)
    total = len(trading_dates)

    ok, fail = 0, 0
    for i, td in enumerate(trading_dates, 1):
        try:
            r_s = await manager.etl_suspend(td)
            r_l = await manager.etl_limit_list(td)
            ok += 1
            if i % 100 == 0 or i == total:
                print(f"   [{i}/{total}] {td} ✓ "
                      f"suspend={r_s.get('suspend_info', 0)}, "
                      f"limit={r_l.get('limit_list_daily', 0)}")
        except Exception as e:
            fail += 1
            if fail <= 5:
                print(f"   [{i}/{total}] {td} ✗ {e}")

    print(f"✓ [步骤4] 完成：{ok} 成功，{fail} 失败，耗时 {time.monotonic() - t0:.1f}s")


async def main():
    setup_logging()

    # 解析参数
    step = "all"
    start_str = "2018-01-01"
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--step" and i < len(sys.argv) - 1:
            step = sys.argv[i + 1]
        elif arg == "--start" and i < len(sys.argv) - 1:
            start_str = sys.argv[i + 1]

    start_date = date.fromisoformat(start_str)
    end_date = date.today()

    print(f"📋 补跑脚本 — 步骤: {step}, 日期范围: {start_date} ~ {end_date}")

    manager = _build_manager()
    t0 = time.monotonic()

    steps = {
        "p3_static": step_p3_static,
        "p2_etl": step_p2_etl,
        "p3_etl": step_p3_etl,
        "p5_etl": step_p5_etl,
    }

    if step == "all":
        run_steps = ["p3_static", "p2_etl", "p3_etl", "p5_etl"]
    elif step in steps:
        run_steps = [step]
    else:
        print(f"❌ 未知步骤: {step}")
        print(f"   可选: {', '.join(steps.keys())}, all")
        sys.exit(1)

    for s in run_steps:
        fn = steps[s]
        if s == "p3_static":
            await fn(manager)
        else:
            await fn(manager, start_date, end_date)

    print(f"\n🎉 全部完成，总耗时 {time.monotonic() - t0:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
