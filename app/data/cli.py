import asyncio
import logging
from datetime import date

import click

from app.config import settings
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.database import async_session_factory
from app.logger import setup_logging

logger = logging.getLogger(__name__)


def _build_manager() -> DataManager:
    client = TushareClient()
    return DataManager(
        session_factory=async_session_factory,
        clients={"tushare": client},
        primary="tushare",
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
    """Incremental sync of today's daily bar data (Tushare 按日期全市场模式)."""
    manager = _build_manager()

    async def _run() -> None:
        today = date.today()
        is_trading = await manager.is_trade_day(today)
        if not is_trading:
            click.echo(f"{today} is not a trading day. Skipping sync.")
            return

        click.echo(f"Syncing daily data for {today} (全市场模式)...")

        # 1. 拉取原始数据到 raw 表
        raw_counts = await manager.sync_raw_daily(today)
        click.echo(f"Raw data: {raw_counts}")

        # 2. ETL 清洗到 stock_daily
        etl_result = await manager.etl_daily(today)
        click.echo(f"ETL: {etl_result['inserted']} rows inserted")

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
    """全量导入复权因子到 stock_daily.adj_factor 字段。

    Tushare 模式下，adj_factor 已在 sync_raw_daily → etl_daily 流程中自动处理。
    此命令用于补全历史数据中缺失的复权因子。
    """
    click.echo("Tushare 模式下，复权因子已在 sync_raw_daily → etl_daily 流程中自动处理。")
    click.echo("如需补全历史数据，请使用 backfill-daily 命令。")


@cli.command("backfill-daily")
@click.option("--start", required=True, help="开始日期 (YYYY-MM-DD)")
@click.option("--end", required=True, help="结束日期 (YYYY-MM-DD)")
def backfill_daily(start: str, end: str) -> None:
    """手动补齐指定日期范围的日线数据（Tushare 按日期全市场模式）。

    只补齐缺失的交易日数据，跳过已有数据的日期和非交易日。
    """
    from app.data.batch import batch_sync_daily

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    manager = _build_manager()

    async def _run() -> None:
        import time

        click.echo(f"开始补齐日期范围：{start_date} ~ {end_date}")

        # 1. 检测缺失日期
        missing_dates = await manager.detect_missing_dates(start_date, end_date)

        if not missing_dates:
            click.echo("指定日期范围内数据完整，无需补齐。")
            return

        click.echo(f"发现 {len(missing_dates)} 个缺失交易日，开始补齐...")

        # 2. 按日期批量同步（sync_raw_daily + etl_daily）
        overall_start = time.monotonic()
        result = await batch_sync_daily(
            session_factory=async_session_factory,
            trade_dates=missing_dates,
            manager=manager,
        )

        overall_elapsed = int(time.monotonic() - overall_start)
        overall_minutes = overall_elapsed // 60
        overall_seconds = overall_elapsed % 60

        click.echo(
            f"\n补齐完成：共 {len(missing_dates)} 个交易日，"
            f"成功 {result['success']} 天，失败 {result['failed']} 天，"
            f"总耗时 {overall_minutes}分{overall_seconds}秒"
        )

    asyncio.run(_run())


@cli.command("init-tushare")
@click.option("--start", default=None, help="开始日期 (YYYY-MM-DD)，默认为 settings.data_start_date")
@click.option("--end", default=None, help="结束日期 (YYYY-MM-DD)，默认为今天")
@click.option("--skip-fina", is_flag=True, help="跳过财务数据同步")
@click.option("--skip-index", is_flag=True, help="跳过指数数据同步")
@click.option("--skip-concept", is_flag=True, help="跳过板块数据同步")
def init_tushare(start: str | None, end: str | None, skip_fina: bool, skip_index: bool, skip_concept: bool) -> None:
    """全量初始化 Tushare 数据：stock_basic → trade_cal → 逐日 daily → fina → 指数/板块 → 技术指标。

    这是一个综合命令，按顺序执行以下步骤：
    1. 同步股票列表 (stock_basic)
    2. 同步交易日历 (trade_cal)
    3. 逐日同步日线数据 (daily + adj_factor + daily_basic)
    4. 同步财务数据 (fina_indicator，可选)
    5. 同步指数数据 (index_basic + index_daily，可选)
    6. 同步板块数据 (concept_index + concept_daily，可选)
    7. 计算技术指标 (technical_daily + index_technical_daily + concept_technical_daily)

    注意：此命令适用于首次初始化或全量重建数据。
    对于日常增量更新，请使用 sync-daily 命令。
    """
    import time
    from app.data.batch import batch_sync_daily

    manager = _build_manager()
    start_date = date.fromisoformat(start) if start else date.fromisoformat(settings.data_start_date)
    end_date = date.fromisoformat(end) if end else date.today()

    async def _run() -> None:
        overall_start = time.monotonic()

        click.echo("=" * 60)
        click.echo("Tushare 数据全量初始化")
        click.echo("=" * 60)
        click.echo(f"日期范围：{start_date} ~ {end_date}")
        click.echo()

        # 步骤 1: 同步股票列表
        click.echo("步骤 1/7: 同步股票列表...")
        stock_result = await manager.sync_stock_list()
        click.echo(f"✓ 股票列表同步完成：{stock_result.get('inserted', 0)} 只股票")
        click.echo()

        # 步骤 2: 同步交易日历
        click.echo("步骤 2/7: 同步交易日历...")
        calendar_result = await manager.sync_trade_calendar(start_date, end_date)
        click.echo(f"✓ 交易日历同步完成：{calendar_result.get('inserted', 0)} 个交易日")
        click.echo()

        # 步骤 3: 逐日同步日线数据
        click.echo("步骤 3/7: 逐日同步日线数据...")
        trading_dates = await manager.get_trade_calendar(start_date, end_date)
        click.echo(f"共需同步 {len(trading_dates)} 个交易日")

        daily_result = await batch_sync_daily(
            session_factory=async_session_factory,
            trade_dates=trading_dates,
            manager=manager,
        )
        click.echo(f"✓ 日线数据同步完成：成功 {daily_result['success']} 天，失败 {daily_result['failed']} 天")
        click.echo()

        # 步骤 4: 同步财务数据（可选）
        if not skip_fina:
            click.echo("步骤 4/7: 同步财务数据...")
            click.echo("⚠️  财务数据同步功能待实现（V2）")
            click.echo()
        else:
            click.echo("步骤 4/7: 跳过财务数据同步")
            click.echo()

        # 步骤 5: 同步指数数据（可选）
        if not skip_index:
            click.echo("步骤 5/7: 同步指数数据...")
            click.echo("⚠️  指数数据同步功能待实现（V2）")
            click.echo()
        else:
            click.echo("步骤 5/7: 跳过指数数据同步")
            click.echo()

        # 步骤 6: 同步板块数据（可选）
        if not skip_concept:
            click.echo("步骤 6/7: 同步板块数据...")
            click.echo("⚠️  板块数据同步功能待实现（V2）")
            click.echo()
        else:
            click.echo("步骤 6/7: 跳过板块数据同步")
            click.echo()

        # 步骤 7: 计算技术指标
        click.echo("步骤 7/7: 计算技术指标...")
        from app.data.indicator import compute_all_stocks

        indicator_result = await compute_all_stocks(
            async_session_factory,
            progress_callback=lambda p, t: click.echo(f"[{p}/{t}] 正在计算技术指标...") if p % 500 == 0 else None,
        )
        click.echo(f"✓ 技术指标计算完成：成功 {indicator_result['success']} 只，失败 {indicator_result['failed']} 只")
        click.echo()

        # 总结
        overall_elapsed = int(time.monotonic() - overall_start)
        overall_minutes = overall_elapsed // 60
        overall_seconds = overall_elapsed % 60

        click.echo("=" * 60)
        click.echo("初始化完成")
        click.echo("=" * 60)
        click.echo(f"总耗时：{overall_minutes}分{overall_seconds}秒")
        click.echo()

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
