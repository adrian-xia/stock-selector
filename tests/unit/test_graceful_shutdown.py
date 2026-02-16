"""测试优雅关闭功能的核心逻辑。"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


def test_shutdown_timeout_value():
    """测试优雅关闭超时时间配置。"""
    from app.main import _shutdown_timeout

    # 验证超时时间为 30 秒
    assert _shutdown_timeout == 30


@pytest.mark.asyncio
async def test_graceful_shutdown_normal():
    """测试优雅关闭 - 正常情况（任务在超时前完成）。"""
    with patch("app.main.stop_scheduler") as mock_stop_scheduler, \
         patch("app.main.close_redis") as mock_close_redis, \
         patch("app.main.engine") as mock_engine:

        # 模拟快速完成的关闭
        mock_stop_scheduler.return_value = AsyncMock()()
        mock_close_redis.return_value = AsyncMock()()
        mock_engine.dispose = AsyncMock()

        from app.main import _graceful_shutdown

        # 执行优雅关闭
        await _graceful_shutdown()

        # 验证所有关闭函数都被调用
        mock_stop_scheduler.assert_called_once()
        mock_close_redis.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_graceful_shutdown_timeout():
    """测试优雅关闭 - 超时情况（任务超时，强制关闭）。"""
    with patch("app.main.stop_scheduler") as mock_stop_scheduler, \
         patch("app.main.close_redis") as mock_close_redis, \
         patch("app.main.engine") as mock_engine, \
         patch("app.main._shutdown_timeout", 0.1):  # 设置很短的超时时间

        # 模拟慢速关闭（超过超时时间）
        async def slow_stop():
            await asyncio.sleep(1)  # 睡眠 1 秒，超过 0.1 秒超时

        mock_stop_scheduler.side_effect = slow_stop
        mock_close_redis.return_value = AsyncMock()()
        mock_engine.dispose = AsyncMock()

        from app.main import _graceful_shutdown

        # 执行优雅关闭（应该触发超时）
        await _graceful_shutdown()

        # 验证 stop_scheduler 被调用了两次（第一次超时，第二次强制停止）
        assert mock_stop_scheduler.call_count == 2
        mock_close_redis.assert_called_once()
        mock_engine.dispose.assert_called_once()
