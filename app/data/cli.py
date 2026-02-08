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
    from app.data.adj_factor import batch_update_adj_factor

    manager = _build_manager()
    bs_client = BaoStockClient()

    async def _run() -> None:
        today = date.today()
        is_trading = await manager.is_trade_day(today)
        if not is_trading:
            click.echo(f"{today} is not a trading day. Skipping sync.")
            return

        stocks = await manager.get_stock_list()
        click.echo(f"Syncing daily data for {len(stocks)} stocks...")

        stats = {"success": 0, "failed": 0, "adj_updated": 0}
        for stock in stocks:
            ts_code = stock["ts_code"]
            try:
                await manager.sync_daily(ts_code, today, today)
                # 同步当日复权因子
                adj_records = await bs_client.fetch_adj_factor(ts_code, today, today)
                if adj_records:
                    updated = await batch_update_adj_factor(
                        async_session_factory, ts_code, adj_records
                    )
                    stats["adj_updated"] += updated
                stats["success"] += 1
            except Exception as e:
                logger.error("Sync failed for %s: %s", ts_code, e)
                stats["failed"] += 1

        click.echo(
            f"Daily sync complete: success={stats['success']}, "
            f"failed={stats['failed']}, adj_factor_updated={stats['adj_updated']}"
        )

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


@cli.command("sync-adj-factor")
@click.option("--force", is_flag=True, help="强制刷新所有股票的复权因子（忽略已有数据）")
def sync_adj_factor(force: bool) -> None:
    """全量导入复权因子到 stock_daily.adj_factor 字段。"""
    from sqlalchemy import text as sa_text

    from app.data.adj_factor import batch_update_adj_factor

    manager = _build_manager()
    bs_client = BaoStockClient()

    async def _run() -> None:
        stocks = await manager.get_stock_list()
        total = len(stocks)

        # 如果不是 force 模式，查询哪些股票还没有 adj_factor
        if not force:
            async with async_session_factory() as session:
                rows = await session.execute(sa_text("""
                    SELECT DISTINCT ts_code FROM stock_daily
                    WHERE adj_factor IS NULL
                """))
                need_sync = {r[0] for r in rows.fetchall()}
            stocks = [s for s in stocks if s["ts_code"] in need_sync]
            click.echo(
                f"需要同步复权因子: {len(stocks)}/{total} 只股票"
                f"（{total - len(stocks)} 只已有数据，跳过）"
            )
        else:
            click.echo(f"强制刷新所有 {total} 只股票的复权因子...")

        total_to_sync = len(stocks)
        if total_to_sync == 0:
            click.echo("所有股票已有复权因子，无需同步。")
            return

        stats = {"success": 0, "failed": 0, "rows_updated": 0}
        for i, stock in enumerate(stocks):
            ts_code = stock["ts_code"]
            list_date = stock.get("list_date")
            try:
                if isinstance(list_date, date):
                    start = list_date
                elif list_date:
                    start = date.fromisoformat(str(list_date))
                else:
                    start = date(2015, 1, 1)
                records = await bs_client.fetch_adj_factor(ts_code, start, date.today())
                if records:
                    updated = await batch_update_adj_factor(
                        async_session_factory, ts_code, records
                    )
                    stats["rows_updated"] += updated
                stats["success"] += 1
            except Exception as e:
                logger.error("复权因子同步失败 %s: %s", ts_code, e)
                stats["failed"] += 1

            if (i + 1) % 100 == 0:
                click.echo(
                    f"[{i + 1}/{total_to_sync}] 同步 {ts_code} — "
                    f"成功={stats['success']}, 失败={stats['failed']}, "
                    f"更新行数={stats['rows_updated']}"
                )

        click.echo(
            f"复权因子同步完成: 成功={stats['success']}, "
            f"失败={stats['failed']}, 更新行数={stats['rows_updated']}"
        )

    asyncio.run(_run())


@cli.command("backfill-daily")
@click.option("--start", required=True, help="开始日期 (YYYY-MM-DD)")
@click.option("--end", required=True, help="结束日期 (YYYY-MM-DD)")
@click.option("--rate-limit", default=None, type=int, help="并发数限制（默认使用配置值）")
def backfill_daily(start: str, end: str, rate_limit: int | None) -> None:
    """手动补齐指定日期范围的日线数据（断点续传）。

    只补齐缺失的交易日数据，跳过已有数据的日期和非交易日。
    """
    from app.data.batch import batch_sync_daily
    from app.data.pool import get_pool

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    # 构建带连接池的 manager
    pool = get_pool()
    clients = {
        "baostock": BaoStockClient(connection_pool=pool),
        "akshare": AKShareClient(),
    }
    manager = DataManager(
        session_factory=async_session_factory,
        clients=clients,
        primary="baostock",
    )

    async def _run() -> None:
        import time

        click.echo(f"开始补齐日期范围：{start_date} ~ {end_date}")

        # 1. 检测缺失日期
        missing_dates = await manager.detect_missing_dates(start_date, end_date)

        if not missing_dates:
            click.echo("指定日期范围内数据完整，无需补齐。")
            return

        click.echo(f"发现 {len(missing_dates)} 个缺失交易日，开始补齐...")

        # 2. 获取所有上市股票
        stocks = await manager.get_stock_list(status="L")
        stock_codes = [s["ts_code"] for s in stocks]
        click.echo(f"共 {len(stock_codes)} 只上市股票")

        # 3. 逐个缺失日期补齐
        total_success = 0
        total_failed = 0
        overall_start = time.monotonic()

        for i, missing_date in enumerate(missing_dates, 1):
            date_start = time.monotonic()
            click.echo(f"\n[{i}/{len(missing_dates)}] 补齐日期：{missing_date}")

            try:
                # 使用批量同步，支持速率限制
                result = await batch_sync_daily(
                    session_factory=async_session_factory,
                    stock_codes=stock_codes,
                    target_date=missing_date,
                    connection_pool=pool,
                    concurrency=rate_limit if rate_limit else settings.daily_sync_concurrency,
                )

                date_elapsed = time.monotonic() - date_start
                total_success += result["success"]
                total_failed += result["failed"]

                click.echo(
                    f"  完成：成功 {result['success']} 只，失败 {result['failed']} 只，"
                    f"耗时 {int(date_elapsed)}秒"
                )

                # 估算剩余时间
                if i < len(missing_dates):
                    avg_time = (time.monotonic() - overall_start) / i
                    remaining_time = int(avg_time * (len(missing_dates) - i))
                    remaining_minutes = remaining_time // 60
                    remaining_seconds = remaining_time % 60
                    click.echo(
                        f"  预计剩余时间：{remaining_minutes}分{remaining_seconds}秒"
                    )

            except Exception as e:
                logger.error("补齐日期 %s 失败：%s", missing_date, e)
                click.echo(f"  失败：{e}")

        overall_elapsed = int(time.monotonic() - overall_start)
        overall_minutes = overall_elapsed // 60
        overall_seconds = overall_elapsed % 60

        click.echo(
            f"\n补齐完成：共 {len(missing_dates)} 个交易日，"
            f"成功 {total_success} 只次，失败 {total_failed} 只次，"
            f"总耗时 {overall_minutes}分{overall_seconds}秒"
        )

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
