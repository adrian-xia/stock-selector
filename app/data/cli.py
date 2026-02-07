import asyncio
import logging
from datetime import date

import click

from app.config import settings
from app.data.akshare import AKShareClient
from app.data.baostock import BaoStockClient
from app.data.manager import DataManager
from app.database import async_session_factory
from app.logger import setup_logging

logger = logging.getLogger(__name__)


def _build_manager() -> DataManager:
    clients = {
        "baostock": BaoStockClient(),
        "akshare": AKShareClient(),
    }
    return DataManager(
        session_factory=async_session_factory,
        clients=clients,
        primary="baostock",
    )


@click.group()
def cli() -> None:
    """A股智能选股系统 - 数据管理 CLI"""
    setup_logging(settings.log_level)


@cli.command("import-stocks")
def import_stocks() -> None:
    """Import A-share stock list into the stocks table."""
    manager = _build_manager()

    async def _run() -> None:
        result = await manager.sync_stock_list()
        click.echo(f"Stock list import complete: {result}")

    asyncio.run(_run())


@cli.command("import-calendar")
@click.option("--start", default="1990-01-01", help="Start date (YYYY-MM-DD)")
@click.option("--end", default=None, help="End date (YYYY-MM-DD), defaults to today")
def import_calendar(start: str, end: str | None) -> None:
    """Import trade calendar into the trade_calendar table."""
    manager = _build_manager()
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end) if end else date.today()

    async def _run() -> None:
        result = await manager.sync_trade_calendar(start_date, end_date)
        click.echo(f"Trade calendar import complete: {result}")

    asyncio.run(_run())


@cli.command("import-daily")
@click.option("--start", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--end", default=None, help="End date, defaults to today")
@click.option("--optimize-indexes", is_flag=True, help="Drop/rebuild indexes for speed")
def import_daily(start: str | None, end: str | None, optimize_indexes: bool) -> None:
    """Full import of daily bar data for all listed stocks."""
    manager = _build_manager()
    end_date = date.fromisoformat(end) if end else date.today()

    async def _run() -> None:
        stocks = await manager.get_stock_list()
        total = len(stocks)
        click.echo(f"Starting daily import for {total} stocks...")

        if optimize_indexes:
            async with async_session_factory() as session:
                from sqlalchemy import text
                await session.execute(text("DROP INDEX IF EXISTS idx_stock_daily_code_date"))
                await session.execute(text("DROP INDEX IF EXISTS idx_stock_daily_trade_date"))
                await session.commit()
            click.echo("Indexes dropped for faster import.")

        stats = {"success": 0, "failed": 0}
        for i, stock in enumerate(stocks):
            ts_code = stock["ts_code"]
            s_date = date.fromisoformat(start) if start else (stock.get("list_date") or date(2020, 1, 1))
            try:
                result = await manager.sync_daily(ts_code, s_date, end_date)
                stats["success"] += 1
            except Exception as e:
                logger.error("Failed to import %s: %s", ts_code, e)
                stats["failed"] += 1

            if (i + 1) % 100 == 0:
                click.echo(
                    f"[{i + 1}/{total}] Importing {ts_code} — "
                    f"success={stats['success']}, failed={stats['failed']}"
                )

        if optimize_indexes:
            async with async_session_factory() as session:
                from sqlalchemy import text
                await session.execute(text(
                    "CREATE INDEX idx_stock_daily_code_date "
                    "ON stock_daily (ts_code, trade_date DESC)"
                ))
                await session.execute(text(
                    "CREATE INDEX idx_stock_daily_trade_date "
                    "ON stock_daily (trade_date)"
                ))
                await session.execute(text("ANALYZE stock_daily"))
                await session.commit()
            click.echo("Indexes rebuilt.")

        click.echo(f"Daily import complete: {stats}")

    asyncio.run(_run())


@cli.command("import-all")
@click.option("--start", default=None, help="Start date for daily bars")
@click.option("--optimize-indexes", is_flag=True, help="Drop/rebuild indexes")
def import_all(start: str | None, optimize_indexes: bool) -> None:
    """Run full import: stocks → calendar → daily bars."""
    ctx = click.get_current_context()
    ctx.invoke(import_stocks)
    ctx.invoke(import_calendar)
    ctx.invoke(import_daily, start=start, optimize_indexes=optimize_indexes)


@cli.command("sync-daily")
def sync_daily() -> None:
    """Incremental sync of today's daily bar data."""
    manager = _build_manager()

    async def _run() -> None:
        today = date.today()
        is_trading = await manager.is_trade_day(today)
        if not is_trading:
            click.echo(f"{today} is not a trading day. Skipping sync.")
            return

        stocks = await manager.get_stock_list()
        click.echo(f"Syncing daily data for {len(stocks)} stocks...")

        stats = {"success": 0, "failed": 0}
        for stock in stocks:
            ts_code = stock["ts_code"]
            try:
                await manager.sync_daily(ts_code, today, today)
                stats["success"] += 1
            except Exception as e:
                logger.error("Sync failed for %s: %s", ts_code, e)
                stats["failed"] += 1

        click.echo(f"Daily sync complete: {stats}")

    asyncio.run(_run())


@cli.command("compute-indicators")
def compute_indicators() -> None:
    """全量计算所有上市股票的技术指标并写入 technical_daily 表。"""
    from app.data.indicator import compute_all_stocks

    def _progress(processed: int, total: int) -> None:
        """进度回调：每 500 只股票打印一次"""
        click.echo(f"[{processed}/{total}] 正在计算技术指标...")

    async def _run() -> None:
        click.echo("开始全量计算技术指标...")
        result = await compute_all_stocks(
            async_session_factory,
            progress_callback=_progress,
        )
        click.echo(
            f"全量计算完成: "
            f"总计={result['total']}, "
            f"成功={result['success']}, "
            f"失败={result['failed']}, "
            f"耗时={result['elapsed_seconds']}秒"
        )

    asyncio.run(_run())


@cli.command("update-indicators")
@click.option("--date", "target_date", default=None, help="目标日期 (YYYY-MM-DD)，默认最新交易日")
def update_indicators(target_date: str | None) -> None:
    """增量计算最新交易日的技术指标并写入 technical_daily 表。"""
    from app.data.indicator import compute_incremental

    parsed_date = date.fromisoformat(target_date) if target_date else None

    def _progress(processed: int, total: int) -> None:
        """进度回调：每 500 只股票打印一次"""
        click.echo(f"[{processed}/{total}] 正在增量计算技术指标...")

    async def _run() -> None:
        click.echo("开始增量计算技术指标...")
        result = await compute_incremental(
            async_session_factory,
            target_date=parsed_date,
            progress_callback=_progress,
        )
        click.echo(
            f"增量计算完成: "
            f"日期={result['trade_date']}, "
            f"总计={result['total']}, "
            f"成功={result['success']}, "
            f"失败={result['failed']}, "
            f"耗时={result['elapsed_seconds']}秒"
        )

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
