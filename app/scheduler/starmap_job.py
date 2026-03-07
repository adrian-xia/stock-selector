"""StarMap 盘后投研调度任务。

独立 cron 任务或挂接在盘后链路中。
"""

import logging
import time
import traceback
from datetime import date

from app.config import settings
from app.database import async_session_factory
from app.scheduler.task_logger import TaskLogger

logger = logging.getLogger(__name__)

_task_logger = TaskLogger(async_session_factory)


async def _send_starmap_report(
    target: date,
    result: dict,
    elapsed: float,
) -> None:
    """生成并推送 StarMap Markdown 报告。"""
    from app.notification import NotificationManager
    from app.research.repository.starmap_repo import StarMapRepository
    from app.scheduler.report import generate_starmap_report

    repo = StarMapRepository(async_session_factory)
    macro_signal = await repo.get_macro_signal(target)
    sectors = await repo.get_sector_resonance(target, top_n=20)
    plans = await repo.get_trade_plans(target)

    summary_text, md_content = generate_starmap_report(
        trade_date=target,
        elapsed=elapsed,
        result=result,
        macro_signal=macro_signal,
        sectors=sectors,
        plans=plans,
    )

    title = (
        f"✅ StarMap 盘后投研完成 — {target}"
        if result.get("status") == "success"
        else f"⚠️ StarMap 盘后投研完成（部分降级）— {target}"
    )
    notifier = NotificationManager()
    await notifier.send_report(
        title=title,
        summary_text=summary_text,
        markdown_content=md_content,
        filename=f"starmap_{target}.md",
    )


async def starmap_job(target_date: date | None = None) -> dict | None:
    """StarMap 投研任务入口。

    可作为独立 cron 或被盘后链路调用。

    Args:
        target_date: 目标交易日，默认今天

    Returns:
        执行结果字典，失败返回 None
    """
    if not settings.starmap_enabled:
        logger.info("[StarMap Job] 已禁用（STARMAP_ENABLED=false），跳过")
        return None

    target = target_date or date.today()
    log_id = await _task_logger.start(
        task_name="starmap_research",
        trigger="cron",
    )

    start = time.monotonic()
    try:
        from app.research.orchestrator import run_starmap

        result = await run_starmap(async_session_factory, target)

        elapsed = time.monotonic() - start
        logger.info(
            "[StarMap Job] 完成: %s, status=%s, 耗时 %.1fs",
            target, result.get("status"), elapsed,
        )

        try:
            await _send_starmap_report(target, result, elapsed)
            logger.info("[StarMap Job] Markdown 报告已生成并推送")
        except Exception:
            logger.warning("[StarMap Job] 报告推送失败\n%s", traceback.format_exc())

        await _task_logger.finish(
            log_id,
            status="success" if result.get("status") == "success" else "partial",
            result_summary={
                "trade_date": target.isoformat(),
                "status": result.get("status"),
                "steps_completed": result.get("steps_completed", []),
                "degrade_flags": result.get("degrade_flags", []),
                "elapsed_seconds": round(elapsed, 1),
            },
        )
        return result

    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "[StarMap Job] 失败: %s, 耗时 %.1fs\n%s",
            target, elapsed, traceback.format_exc(),
        )
        try:
            from app.notification import NotificationManager

            notifier = NotificationManager()
            await notifier.send(
                level="error",
                title="❌ StarMap 盘后投研失败",
                message=f"日期 {target}\n耗时 {elapsed:.1f}s\n错误: {traceback.format_exc().splitlines()[-1]}",
            )
        except Exception:
            logger.warning("[StarMap Job] 失败通知发送失败\n%s", traceback.format_exc())
        await _task_logger.finish(
            log_id,
            status="failed",
            error_message=traceback.format_exc(),
        )
        return None


async def starmap_cron_job() -> None:
    """独立 cron 入口（无参数，自动取今日日期）。"""
    await starmap_job()
