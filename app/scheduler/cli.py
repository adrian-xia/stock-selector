"""调度器 CLI 命令：手动触发任务链或单个任务。

用法：
    python -m app.scheduler.cli run-chain [--date 2024-06-15]
    python -m app.scheduler.cli run-job sync-daily [--date 2024-06-15]
"""

import asyncio
import logging
from datetime import date

import click

from app.config import settings
from app.logger import setup_logging

logger = logging.getLogger(__name__)

# 可用的单步任务映射
JOB_MAP = {
    "pipeline": "pipeline_step",
    "sync-stocks": "sync_stock_list_job",
    "retry-failed": "retry_failed_stocks_job",
}


@click.group()
def cli() -> None:
    """A股智能选股系统 - 调度器 CLI"""
    setup_logging(settings.log_level)


@cli.command("run-chain")
@click.option(
    "--date", "target_date", default=None,
    help="目标日期（YYYY-MM-DD），默认今天",
)
def run_chain(target_date: str | None) -> None:
    """手动触发完整盘后链路。"""
    from app.scheduler.jobs import run_post_market_chain

    target = date.fromisoformat(target_date) if target_date else date.today()
    click.echo(f"触发盘后链路：{target}")
    asyncio.run(run_post_market_chain(target))


@cli.command("run-job")
@click.argument("job_name")
@click.option(
    "--date", "target_date", default=None,
    help="目标日期（YYYY-MM-DD），默认今天",
)
def run_job(job_name: str, target_date: str | None) -> None:
    """手动触发单个任务步骤。

    可用任务：pipeline, sync-stocks, retry-failed
    """
    if job_name not in JOB_MAP:
        available = ", ".join(JOB_MAP.keys())
        click.echo(f"错误：未知任务 '{job_name}'，可用任务：{available}", err=True)
        raise SystemExit(1)

    import app.scheduler.jobs as jobs_module

    func_name = JOB_MAP[job_name]
    func = getattr(jobs_module, func_name)

    target = date.fromisoformat(target_date) if target_date else date.today()
    click.echo(f"触发任务 {job_name}：{target}")

    # sync_stock_list_job 和 retry_failed_stocks_job 不接受 target_date 参数
    if job_name in ("sync-stocks", "retry-failed"):
        asyncio.run(func())
    else:
        asyncio.run(func(target))


# 支持 python -m app.scheduler.cli
if __name__ == "__main__":
    cli()
