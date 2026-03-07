"""测试 StarMap 调度任务。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scheduler.starmap_job import starmap_cron_job, starmap_job


@pytest.mark.asyncio
@patch("app.scheduler.starmap_job._task_logger", new_callable=AsyncMock)
@patch("app.scheduler.starmap_job._send_starmap_report", new_callable=AsyncMock)
@patch("app.scheduler.starmap_job.settings")
@patch("app.research.orchestrator.run_starmap", new_callable=AsyncMock)
async def test_starmap_job_generates_and_pushes_report(
    mock_run_starmap: AsyncMock,
    mock_settings: MagicMock,
    mock_send_report: AsyncMock,
    mock_task_logger: AsyncMock,
):
    """StarMap 成功执行后应生成并推送 Markdown 报告。"""
    mock_settings.starmap_enabled = True
    mock_run_starmap.return_value = {
        "status": "success",
        "steps_completed": ["readiness_probe", "news_pipeline"],
        "degrade_flags": [],
        "errors": [],
        "stats": {"news_fetched": 10},
    }

    result = await starmap_job(date(2026, 3, 7))

    assert result is not None
    assert result["status"] == "success"
    mock_send_report.assert_awaited_once()
    mock_task_logger.start.assert_awaited_once()
    mock_task_logger.finish.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.scheduler.starmap_job.starmap_job", new_callable=AsyncMock)
async def test_starmap_cron_job_skips_when_today_already_ran(
    mock_starmap_job: AsyncMock,
):
    """若当天已成功执行过 StarMap，则独立 cron 应跳过重复运行。"""
    mock_session = AsyncMock()
    mock_session.scalar.return_value = "success"
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with patch("app.scheduler.starmap_job.async_session_factory", mock_session_factory):
        await starmap_cron_job()

    mock_starmap_job.assert_not_awaited()
