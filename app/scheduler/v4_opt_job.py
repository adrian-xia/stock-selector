"""V4 量价配合策略独立优化任务。

与 weekly_market_opt_job 并行调度，使用 V4 专用回测引擎（逐日模拟 + 零 SQL 内存架构）。
"""

import json
import logging
import time
from datetime import date
from uuid import uuid4

from sqlalchemy import text

from app.config import settings
from app.database import async_session_factory
from app.v4backtest.engine import DEFAULT_PARAMS
from app.v4backtest.grid_search import run_grid_search

logger = logging.getLogger(__name__)

# 阶段一：核心 4 参数，81 组合
V4_OPT_PARAM_GRID = {
    "min_t0_pct_chg": [5.0, 6.0, 7.0],
    "min_washout_days": [2, 3, 4],
    "max_vol_shrink_ratio": [0.30, 0.40, 0.50],
    "ma_support_tolerance": [0.010, 0.015, 0.020],
}


async def _get_latest_trade_date() -> date:
    """查询最近的交易日。"""
    async with async_session_factory() as session:
        r = await session.execute(text(
            "SELECT cal_date FROM trade_calendar "
            "WHERE is_open=true AND cal_date <= CURRENT_DATE "
            "ORDER BY cal_date DESC LIMIT 1"
        ))
        row = r.fetchone()
        return row[0] if row else date.today()


async def weekly_v4_opt_job(
    *,
    param_grid: dict | None = None,
    start_override: date | None = None,
    end_override: date | None = None,
) -> dict | None:
    """V4 量价配合策略每周参数优化。

    Args:
        param_grid: 自定义参数网格（None 时使用 V4_OPT_PARAM_GRID）
        start_override: 覆盖回测起始日期
        end_override: 覆盖回测结束日期

    Returns:
        优化结果摘要 dict，失败返回 None
    """
    if not settings.v4_opt_enabled and param_grid is None:
        logger.info("[v4-opt] V4 优化已禁用")
        return None

    t_start = time.monotonic()
    logger.info("=== 开始 V4 量价配合策略参数优化 ===")

    # 1. 确定日期范围
    start_date = start_override or date.fromisoformat(settings.v4_opt_lookback_start)
    if end_override:
        end_date = end_override
    elif settings.v4_opt_lookback_end:
        end_date = date.fromisoformat(settings.v4_opt_lookback_end)
    else:
        end_date = await _get_latest_trade_date()

    grid = param_grid or V4_OPT_PARAM_GRID
    grid_search_id = str(uuid4())

    logger.info(
        "[v4-opt] 回测区间 %s ~ %s, grid_search_id=%s",
        start_date, end_date, grid_search_id,
    )

    try:
        # 2. 执行网格搜索
        results = await run_grid_search(
            session_factory=async_session_factory,
            start_date=start_date,
            end_date=end_date,
            param_grid=grid,
            max_concurrency=settings.v4_opt_max_concurrency,
        )

        elapsed = time.monotonic() - t_start

        if not results:
            logger.warning("[v4-opt] 无有效结果")
            await _send_failure_notification("无有效结果", elapsed)
            return None

        # 3. 批量写入 v4_backtest_results
        async with async_session_factory() as session:
            for rank, r in enumerate(results, 1):
                m = r.metrics
                await session.execute(text("""
                    INSERT INTO v4_backtest_results
                        (run_id, params, backtest_start, backtest_end,
                         total_signals, signals_per_month,
                         win_rate_1d, win_rate_3d, win_rate_5d, win_rate_10d,
                         avg_ret_5d, profit_loss_ratio, max_drawdown,
                         sharpe_ratio, composite_score,
                         is_grid_search, grid_search_id, rank_in_grid)
                    VALUES (:rid, CAST(:p AS json), :s, :e,
                            :ts, :spm,
                            :wr1, :wr3, :wr5, :wr10,
                            :ar5, :plr, :md,
                            :sr, :cs,
                            true, :gid, :rank)
                """), {
                    "rid": str(uuid4()), "p": json.dumps(r.params),
                    "s": start_date, "e": end_date,
                    "ts": m.total_signals, "spm": m.signals_per_month,
                    "wr1": m.win_rate_1d, "wr3": m.win_rate_3d,
                    "wr5": m.win_rate_5d, "wr10": m.win_rate_10d,
                    "ar5": m.avg_ret_5d, "plr": m.profit_loss_ratio,
                    "md": m.max_drawdown, "sr": m.sharpe_ratio,
                    "cs": r.score,
                    "gid": grid_search_id, "rank": rank,
                })

            # 4. 自动应用最佳参数
            applied = False
            if settings.v4_opt_auto_apply:
                best = results[0]
                merged = {**DEFAULT_PARAMS, **best.params}
                await session.execute(
                    text(
                        "UPDATE strategies SET params=CAST(:p AS jsonb), "
                        "updated_at=NOW() WHERE name='volume-price-pattern'"
                    ),
                    {"p": json.dumps(merged)},
                )
                applied = True
                logger.info("[v4-opt] 最佳参数已应用: score=%.4f", best.score)

            await session.commit()

        # 5. 发送 Telegram 通知
        await _send_success_notification(
            results, grid_search_id, start_date, end_date, elapsed, applied,
        )

        logger.info(
            "=== V4 参数优化完成: %d 组, 最佳 %.4f, 耗时 %.1fs ===",
            len(results), results[0].score, elapsed,
        )
        return {
            "grid_search_id": grid_search_id,
            "total_combos": len(results),
            "best_score": results[0].score,
            "best_params": results[0].params,
            "elapsed": round(elapsed, 1),
            "applied": applied,
        }

    except Exception as e:
        elapsed = time.monotonic() - t_start
        logger.exception("[v4-opt] 优化失败")
        await _send_failure_notification(str(e), elapsed)
        return None


async def _send_success_notification(
    results, grid_search_id, start_date, end_date, elapsed, applied,
) -> None:
    """发送优化成功的 Telegram 通知。"""
    try:
        from app.notification import NotificationManager
        from app.scheduler.report import generate_v4_opt_report

        notifier = NotificationManager()
        summary_text, md_content = generate_v4_opt_report(
            results=results,
            elapsed=elapsed,
            start_date=start_date,
            end_date=end_date,
            applied=applied,
        )
        await notifier.send_report(
            title="🐉 V4 量价配合策略参数优化完成",
            summary_text=summary_text,
            markdown_content=md_content,
            filename=f"v4_opt_{date.today()}.md",
        )
    except Exception as e:
        logger.warning("[v4-opt] Telegram 通知发送失败: %s", e)


async def _send_failure_notification(error_msg: str, elapsed: float) -> None:
    """发送优化失败的 Telegram 通知。"""
    try:
        from app.notification import NotificationManager

        notifier = NotificationManager()
        await notifier.send(
            level="error",
            title="🐉 V4 参数优化失败",
            message=f"⏱ 耗时 {elapsed:.0f}s\n❌ {error_msg}",
        )
    except Exception as e:
        logger.warning("[v4-opt] 失败通知发送失败: %s", e)
