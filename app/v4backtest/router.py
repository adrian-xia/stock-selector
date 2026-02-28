"""V4 回测 API 路由。"""

import asyncio
import json
import logging
from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.database import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/v4backtest", tags=["v4-backtest"])


class BacktestRequest(BaseModel):
    start_date: date = date(2024, 7, 1)
    end_date: date = date(2025, 12, 31)
    params: dict | None = None


class GridSearchRequest(BaseModel):
    start_date: date = date(2024, 7, 1)
    end_date: date = date(2025, 12, 31)
    param_grid: dict | None = None
    max_concurrency: int = 8


@router.post("/run")
async def run_backtest_api(req: BacktestRequest):
    """启动单次回测。"""
    import asyncio
    from app.v4backtest.engine import run_backtest
    from app.v4backtest.evaluator import evaluate_signals
    from app.v4backtest.grid_search import fill_returns

    run_id = str(uuid4())

    async def _do():
        async with async_session_factory() as session:
            sigs = await run_backtest(session, req.params, req.start_date, req.end_date)
            await fill_returns(session, sigs)
            metrics = evaluate_signals(sigs)
            # 保存结果
            await session.execute(text("""
                INSERT INTO v4_backtest_results
                    (run_id, params, backtest_start, backtest_end,
                     total_signals, signals_per_month, win_rate_5d,
                     profit_loss_ratio, max_drawdown, sharpe_ratio,
                     composite_score, signals)
                VALUES (:rid, :p, :s, :e, :ts, :spm, :wr5,
                        :plr, :md, :sr, :cs, :sigs)
            """), {
                "rid": run_id, "p": json.dumps(req.params or {}),
                "s": req.start_date, "e": req.end_date,
                "ts": metrics.total_signals, "spm": metrics.signals_per_month,
                "wr5": metrics.win_rate_5d, "plr": metrics.profit_loss_ratio,
                "md": metrics.max_drawdown, "sr": metrics.sharpe_ratio,
                "cs": round(metrics.win_rate_5d * 0.4 + min(metrics.profit_loss_ratio, 5) / 5 * 0.3 + min(metrics.sharpe_ratio, 3) / 3 * 0.3, 4),
                "sigs": json.dumps([{"ts_code": s.ts_code, "date": str(s.signal_date), "ret_5d": s.ret_5d} for s in sigs]),
            })
            await session.commit()

    asyncio.create_task(_do())
    return {"run_id": run_id, "status": "running"}


@router.get("/results")
async def get_results(
    run_id: str | None = Query(None),
    limit: int = Query(20, le=100),
):
    """查询回测结果。"""
    async with async_session_factory() as session:
        if run_id:
            r = await session.execute(text(
                "SELECT * FROM v4_backtest_results WHERE run_id=:rid"
            ), {"rid": run_id})
        else:
            r = await session.execute(text(
                "SELECT * FROM v4_backtest_results ORDER BY composite_score DESC NULLS LAST LIMIT :lim"
            ), {"lim": limit})
        rows = r.fetchall()
        return {"results": [dict(row._mapping) for row in rows], "total": len(rows)}


class V4OptRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    param_grid: dict | None = None
    max_concurrency: int = 4
    auto_apply: bool = True


@router.post("/optimize")
async def run_v4_optimization(req: V4OptRequest):
    """手动触发 V4 参数优化（后台异步执行）。"""
    from app.v4backtest.engine import DEFAULT_PARAMS
    from app.v4backtest.grid_search import run_grid_search
    from app.scheduler.v4_opt_job import V4_OPT_PARAM_GRID, _get_latest_trade_date

    grid_search_id = str(uuid4())

    # 确定日期范围
    start_date = req.start_date or date(2024, 7, 1)
    end_date = req.end_date or await _get_latest_trade_date()
    param_grid = req.param_grid or V4_OPT_PARAM_GRID

    async def _do():
        import json
        import time
        from app.config import settings
        from app.notification import NotificationManager
        from app.scheduler.report import generate_v4_opt_report

        t_start = time.monotonic()
        try:
            results = await run_grid_search(
                session_factory=async_session_factory,
                start_date=start_date,
                end_date=end_date,
                param_grid=param_grid,
                max_concurrency=req.max_concurrency,
            )
            elapsed = time.monotonic() - t_start

            auto_applied = False
            async with async_session_factory() as session:
                for rank, r in enumerate(results, 1):
                    m = r.metrics
                    merged = {**DEFAULT_PARAMS, **r.params}
                    await session.execute(text("""
                        INSERT INTO v4_backtest_results (
                            run_id, grid_search_id, rank_in_grid, is_grid_search,
                            params, backtest_start, backtest_end,
                            total_signals, signals_per_month,
                            win_rate_1d, win_rate_3d, win_rate_5d, win_rate_10d,
                            avg_ret_5d, profit_loss_ratio, max_drawdown, sharpe_ratio,
                            composite_score
                        ) VALUES (
                            :run_id, :gsid, :rank, true,
                            CAST(:params AS json), :bs, :be,
                            :ts, :spm, :wr1, :wr3, :wr5, :wr10,
                            :ar5, :plr, :md, :sr, :cs
                        )
                    """), {
                        "run_id": str(uuid4()), "gsid": grid_search_id,
                        "rank": rank, "params": json.dumps(merged),
                        "bs": start_date, "be": end_date,
                        "ts": m.total_signals, "spm": m.signals_per_month,
                        "wr1": m.win_rate_1d, "wr3": m.win_rate_3d,
                        "wr5": m.win_rate_5d, "wr10": m.win_rate_10d,
                        "ar5": m.avg_ret_5d, "plr": m.profit_loss_ratio,
                        "md": m.max_drawdown, "sr": m.sharpe_ratio,
                        "cs": r.score,
                    })

                if req.auto_apply and results:
                    best = results[0]
                    merged = {**DEFAULT_PARAMS, **best.params}
                    await session.execute(text("""
                        UPDATE strategies SET params=CAST(:params AS jsonb), updated_at=NOW()
                        WHERE name='volume-price-pattern'
                    """), {"params": json.dumps(merged)})
                    auto_applied = True

                await session.commit()

            notifier = NotificationManager()
            summary_text, md_content = generate_v4_opt_report(
                results=results, elapsed=elapsed,
                start_date=start_date, end_date=end_date,
                auto_applied=auto_applied,
            )
            await notifier.send_report(
                title="🐉 V4 量价配合策略 — 手动优化完成",
                summary_text=summary_text,
                markdown_content=md_content,
                filename=f"v4_opt_{date.today()}.md",
            )
        except Exception as e:
            elapsed = time.monotonic() - t_start
            logger.exception("[v4-opt-api] 优化失败（耗时 %.1fs）", elapsed)
            try:
                notifier = NotificationManager()
                await notifier.send("error", "❌ V4 手动优化失败", f"耗时 {elapsed:.0f}s\n错误: {e}")
            except Exception:
                pass

    asyncio.create_task(_do())
    return {
        "grid_search_id": grid_search_id,
        "status": "running",
        "start_date": str(start_date),
        "end_date": str(end_date),
        "param_grid": param_grid,
    }


@router.get("/optimize/latest")
async def get_latest_v4_opt(top_n: int = Query(10, le=50)):
    """查询最近一次 V4 优化结果（最新批次的 Top N）。"""
    async with async_session_factory() as session:
        # 找最新的 grid_search_id
        r = await session.execute(text("""
            SELECT grid_search_id, MAX(created_at) AS latest
            FROM v4_backtest_results
            WHERE is_grid_search = true AND grid_search_id IS NOT NULL
            GROUP BY grid_search_id
            ORDER BY latest DESC
            LIMIT 1
        """))
        row = r.fetchone()
        if not row:
            return {"grid_search_id": None, "results": [], "total": 0}

        gsid = row.grid_search_id
        r2 = await session.execute(text("""
            SELECT run_id, rank_in_grid, params, backtest_start, backtest_end,
                   total_signals, signals_per_month,
                   win_rate_1d, win_rate_3d, win_rate_5d, win_rate_10d,
                   avg_ret_5d, profit_loss_ratio, max_drawdown, sharpe_ratio,
                   composite_score, created_at
            FROM v4_backtest_results
            WHERE grid_search_id = :gsid
            ORDER BY rank_in_grid ASC
            LIMIT :n
        """), {"gsid": gsid, "n": top_n})
        rows = r2.fetchall()
        return {
            "grid_search_id": gsid,
            "results": [dict(row._mapping) for row in rows],
            "total": len(rows),
        }

