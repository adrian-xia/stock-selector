"""TaskLogger 和任务日志查询 API 单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.scheduler.task_logger import TaskLogger


def _make_mock_factory(scalar_value=42):
    """创建模拟的 session factory。"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = scalar_value
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    # async_sessionmaker() 返回 AsyncSession，它本身是 async context manager
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    def factory():
        return mock_session

    return factory, mock_session


class TestTaskLogger:
    """TaskLogger 测试。"""

    @pytest.mark.asyncio
    async def test_start_inserts_running_record(self):
        """start() 应插入 running 状态记录。"""
        factory, mock_session = _make_mock_factory(scalar_value=42)
        task_logger = TaskLogger(factory)
        log_id = await task_logger.start("test_task")

        assert log_id == 42
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_finish_updates_record(self):
        """finish() 应更新记录状态。"""
        factory, mock_session = _make_mock_factory()
        task_logger = TaskLogger(factory)
        await task_logger.finish(42, status="success", result_summary={"count": 10})

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_success(self):
        """track() 成功时应记录 start + finish(success)。"""
        factory, mock_session = _make_mock_factory(scalar_value=1)
        task_logger = TaskLogger(factory)

        async with task_logger.track("test_task") as ctx:
            ctx["result"] = {"ok": True}

        # start + finish = 2 次 execute
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_track_failure(self):
        """track() 异常时应记录 start + finish(failed) 并重新抛出。"""
        factory, mock_session = _make_mock_factory(scalar_value=1)
        task_logger = TaskLogger(factory)

        with pytest.raises(ValueError, match="boom"):
            async with task_logger.track("test_task"):
                raise ValueError("boom")

        # start + finish(failed) = 2 次 execute
        assert mock_session.execute.call_count == 2
