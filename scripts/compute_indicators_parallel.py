"""并行计算全市场技术指标。

将标的列表分组，多协程并发计算，大幅提升全量计算速度。
支持股票（stock）、板块（concept）或全部（all）。

用法：
    APP_ENV_FILE=.env.prod uv run python -m scripts.compute_indicators_parallel [--workers 8] [--target stock|concept|all]
"""

import argparse
import asyncio
import logging
import time
from typing import Type

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase

from app.data.indicator import (
    _build_indicator_row,
    _upsert_technical_rows_generic,
    compute_single_stock_indicators,
)
from app.database import async_session_factory
from app.models.concept import ConceptDaily, ConceptTechnicalDaily
from app.models.market import Stock, StockDaily
from app.models.technical import TechnicalDaily

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def compute_one(
    ts_code: str,
    sem: asyncio.Semaphore,
    source_table: Type[DeclarativeBase],
    target_table: Type[DeclarativeBase],
) -> tuple[str, int, bool]:
    """计算单个标的的技术指标。"""
    async with sem:
        try:
            async with async_session_factory() as session:
                stmt = (
                    select(source_table)
                    .where(source_table.ts_code == ts_code)
                    .order_by(source_table.trade_date.asc())
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

            if not rows:
                return ts_code, 0, True

            records = [{
                "trade_date": r.trade_date,
                "open": float(r.open) if r.open else 0.0,
                "high": float(r.high) if r.high else 0.0,
                "low": float(r.low) if r.low else 0.0,
                "close": float(r.close) if r.close else 0.0,
                "vol": float(r.vol) if r.vol else 0.0,
            } for r in rows]
            df = pd.DataFrame(records)

            df_ind = await asyncio.to_thread(compute_single_stock_indicators, df)

            ind_rows = [
                _build_indicator_row(ts_code, row["trade_date"], row)
                for _, row in df_ind.iterrows()
            ]

            async with async_session_factory() as session:
                await _upsert_technical_rows_generic(session, ind_rows, target_table)
                await session.commit()

            return ts_code, len(ind_rows), True
        except Exception as e:
            logger.error("计算 %s 失败: %s", ts_code, e)
            return ts_code, 0, False


async def run_batch(
    label: str,
    codes: list[str],
    workers: int,
    source_table: Type[DeclarativeBase],
    target_table: Type[DeclarativeBase],
):
    """并行计算一批标的的技术指标。"""
    total = len(codes)
    logger.info("开始计算 %s 技术指标：%d 个标的，%d 并发", label, total, workers)
    start = time.time()

    sem = asyncio.Semaphore(workers)
    success = failed = total_rows = done = 0

    tasks = [compute_one(code, sem, source_table, target_table) for code in codes]

    for coro in asyncio.as_completed(tasks):
        ts_code, rows, ok = await coro
        done += 1
        if ok:
            success += 1
            total_rows += rows
        else:
            failed += 1

        if done % 200 == 0 or done == total:
            elapsed = time.time() - start
            speed = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / speed if speed > 0 else 0
            logger.info(
                "[%s %d/%d] 成功=%d 失败=%d 累计%d行 %.1f/s ETA %.0fs",
                label, done, total, success, failed, total_rows, speed, eta,
            )

    elapsed = time.time() - start
    logger.info(
        "%s 完成：%d 成功, %d 失败, %d 行, 耗时 %.1fs (%.1f分钟)",
        label, success, failed, total_rows, elapsed, elapsed / 60,
    )


async def main(workers: int = 8, target: str = "all"):
    """并行计算全市场技术指标。"""

    if target in ("stock", "all"):
        async with async_session_factory() as session:
            stmt = select(Stock.ts_code).where(Stock.list_status == "L")
            result = await session.execute(stmt)
            stock_codes = [row[0] for row in result.all()]
        await run_batch("股票", stock_codes, workers, StockDaily, TechnicalDaily)

    if target in ("concept", "all"):
        async with async_session_factory() as session:
            stmt = select(ConceptDaily.ts_code).distinct()
            result = await session.execute(stmt)
            concept_codes = [row[0] for row in result.all()]
        await run_batch("板块", concept_codes, workers, ConceptDaily, ConceptTechnicalDaily)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="并行计算全市场技术指标")
    parser.add_argument("--workers", type=int, default=8, help="并发数（默认 8）")
    parser.add_argument("--target", choices=["stock", "concept", "all"], default="all", help="计算目标")
    args = parser.parse_args()
    asyncio.run(main(workers=args.workers, target=args.target))
