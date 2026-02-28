"""V4 回测 API 路由。"""

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
                "rid": run_id, "p": req.params or {},
                "s": req.start_date, "e": req.end_date,
                "ts": metrics.total_signals, "spm": metrics.signals_per_month,
                "wr5": metrics.win_rate_5d, "plr": metrics.profit_loss_ratio,
                "md": metrics.max_drawdown, "sr": metrics.sharpe_ratio,
                "cs": round(metrics.win_rate_5d * 0.4 + min(metrics.profit_loss_ratio, 5) / 5 * 0.3 + min(metrics.sharpe_ratio, 3) / 3 * 0.3, 4),
                "sigs": [{"ts_code": s.ts_code, "date": str(s.signal_date), "ret_5d": s.ret_5d} for s in sigs],
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
