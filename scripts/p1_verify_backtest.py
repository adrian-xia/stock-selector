"""P1 回测验证脚本：高位回落企稳策略改造前后对比。

验证内容：
1. 确认 high_60 字段存在且非空
2. 单日 Pipeline 运行测试
3. 全量回测（2024-01 至今）
"""

import asyncio
import json
import logging
import time
from datetime import date, timedelta

from sqlalchemy import text

from app.database import async_session_factory
from app.strategy.pipeline import execute_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def verify_high_60_field() -> dict:
    """C1: 验证 high_60 字段在 technical_daily 表中存在且非空。"""
    async with async_session_factory() as session:
        # 统计最近交易日的 high_60 非空率
        result = await session.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(high_20) AS has_high_20,
                COUNT(high_60) AS has_high_60,
                AVG(high_20) AS avg_high_20,
                AVG(high_60) AS avg_high_60
            FROM technical_daily
            WHERE trade_date = (SELECT MAX(trade_date) FROM technical_daily)
        """))
        row = result.fetchone()
        stats = {
            "total": row[0],
            "has_high_20": row[1],
            "has_high_60": row[2],
            "high_20_coverage": f"{row[1]/row[0]*100:.1f}%" if row[0] > 0 else "N/A",
            "high_60_coverage": f"{row[2]/row[0]*100:.1f}%" if row[0] > 0 else "N/A",
            "avg_high_20": round(float(row[3]), 2) if row[3] else None,
            "avg_high_60": round(float(row[4]), 2) if row[4] else None,
        }
        logger.info("C1 字段验证：%s", json.dumps(stats, ensure_ascii=False))
        return stats


async def run_single_day_pipeline() -> dict:
    """C1: 单日 Pipeline 运行测试。"""
    # 获取最近交易日
    async with async_session_factory() as session:
        result = await session.execute(text(
            "SELECT MAX(trade_date) FROM stock_daily WHERE vol > 0"
        ))
        latest_date = result.scalar()

    logger.info("单日 Pipeline 测试，目标日期：%s", latest_date)

    pipeline_result = await execute_pipeline(
        session_factory=async_session_factory,
        strategy_names=["peak-pullback-stabilization"],
        target_date=latest_date,
        top_n=50,
    )

    stats = {
        "target_date": str(latest_date),
        "picks_count": len(pipeline_result.picks),
        "layer_stats": pipeline_result.layer_stats,
        "elapsed_ms": pipeline_result.elapsed_ms,
        "picks": [
            {
                "ts_code": p.ts_code,
                "name": p.name,
                "close": p.close,
                "pct_chg": p.pct_chg,
                "score": p.weighted_score,
            }
            for p in pipeline_result.picks[:10]
        ],
    }
    logger.info("C1 单日结果：%d 只股票命中，耗时 %d ms", stats["picks_count"], stats["elapsed_ms"])
    return stats


async def run_backtest_range(
    start_date: date,
    end_date: date,
) -> dict:
    """C2: 全量回测（按交易日逐日跑 Pipeline）。"""
    # 获取日期范围内的交易日
    async with async_session_factory() as session:
        result = await session.execute(text("""
            SELECT DISTINCT trade_date
            FROM stock_daily
            WHERE trade_date BETWEEN :start AND :end
              AND vol > 0
            ORDER BY trade_date
        """), {"start": start_date, "end": end_date})
        trade_dates = [row[0] for row in result.fetchall()]

    logger.info("回测区间：%s ~ %s，共 %d 个交易日", start_date, end_date, len(trade_dates))

    total_picks = 0
    daily_results = []
    start_time = time.time()

    for i, td in enumerate(trade_dates):
        try:
            result = await execute_pipeline(
                session_factory=async_session_factory,
                strategy_names=["peak-pullback-stabilization"],
                target_date=td,
                top_n=50,
            )
            picks_count = len(result.picks)
            total_picks += picks_count
            daily_results.append({
                "date": str(td),
                "picks": picks_count,
                "elapsed_ms": result.elapsed_ms,
            })

            if (i + 1) % 50 == 0:
                logger.info("回测进度：%d/%d 交易日", i + 1, len(trade_dates))

        except Exception as e:
            logger.error("日期 %s 执行失败：%s", td, e)
            daily_results.append({"date": str(td), "picks": 0, "error": str(e)})

    elapsed = round(time.time() - start_time, 1)
    active_days = sum(1 for d in daily_results if d["picks"] > 0)
    picks_list = [d["picks"] for d in daily_results if d["picks"] > 0]

    # 从 strategy_picks 读取命中率数据
    hit_stats = await _get_hit_stats(start_date, end_date)

    summary = {
        "period": f"{start_date} ~ {end_date}",
        "total_trade_days": len(trade_dates),
        "active_days": active_days,
        "total_picks": total_picks,
        "avg_picks_per_active_day": round(sum(picks_list) / len(picks_list), 1) if picks_list else 0,
        "max_picks_per_day": max(picks_list) if picks_list else 0,
        "elapsed_seconds": elapsed,
        "hit_stats": hit_stats,
    }

    logger.info("C2 全量回测完成：%s", json.dumps(summary, ensure_ascii=False, default=str))
    return summary


async def _get_hit_stats(start_date: date, end_date: date) -> dict:
    """从 strategy_picks 读取命中率统计。"""
    async with async_session_factory() as session:
        result = await session.execute(text("""
            SELECT
                COUNT(*) AS total_picks,
                COUNT(CASE WHEN return_5d > 0 THEN 1 END) AS win_5d,
                AVG(return_5d) AS avg_return_5d,
                MAX(return_5d) AS max_return_5d,
                MIN(return_5d) AS min_return_5d
            FROM strategy_picks
            WHERE strategy_name = 'peak-pullback-stabilization'
              AND pick_date BETWEEN :start AND :end
              AND return_5d IS NOT NULL
        """), {"start": start_date, "end": end_date})
        row = result.fetchone()

        if row and row[0] > 0:
            return {
                "total_with_return": row[0],
                "win_5d_count": row[1],
                "hit_rate_5d": f"{row[1]/row[0]*100:.1f}%",
                "avg_return_5d": f"{float(row[2]):.2f}%",
                "max_return_5d": f"{float(row[3]):.2f}%",
                "min_return_5d": f"{float(row[4]):.2f}%",
            }
        return {"note": "无已回填的收益率数据（需等待命中率回填任务运行）"}


async def main() -> None:
    """执行全部验证步骤。"""
    results = {}

    # C1: 字段验证
    logger.info("=" * 60)
    logger.info("C1: 验证 high_60 字段")
    logger.info("=" * 60)
    results["field_check"] = await verify_high_60_field()

    # C1: 单日 Pipeline 测试
    logger.info("=" * 60)
    logger.info("C1: 单日 Pipeline 测试")
    logger.info("=" * 60)
    results["single_day"] = await run_single_day_pipeline()

    # C2: 全量回测
    logger.info("=" * 60)
    logger.info("C2: 全量回测 2024-01 至今")
    logger.info("=" * 60)
    results["backtest"] = await run_backtest_range(
        start_date=date(2024, 1, 1),
        end_date=date(2026, 2, 28),
    )

    # 输出汇总
    logger.info("=" * 60)
    logger.info("验证结果汇总")
    logger.info("=" * 60)
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))

    # 保存结果到文件
    with open("scripts/p1_verification_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    logger.info("结果已保存到 scripts/p1_verification_results.json")


if __name__ == "__main__":
    asyncio.run(main())
