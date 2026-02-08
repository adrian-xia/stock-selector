"""测试优雅关闭功能的核心逻辑。"""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

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
         patch("app.main.close_pool") as mock_close_pool, \
         patch("app.main.close_redis") as mock_close_redis, \
         patch("app.main.engine") as mock_engine:

        # 模拟快速完成的关闭
        mock_stop_scheduler.return_value = AsyncMock()()
        mock_close_pool.return_value = AsyncMock()()
        mock_close_redis.return_value = AsyncMock()()
        mock_engine.dispose = AsyncMock()

        from app.main import _graceful_shutdown

        # 执行优雅关闭
        await _graceful_shutdown()

        # 验证所有关闭函数都被调用
        mock_stop_scheduler.assert_called_once()
        mock_close_pool.assert_called_once()
        mock_close_redis.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_graceful_shutdown_timeout():
    """测试优雅关闭 - 超时情况（任务超时，强制关闭）。"""
    with patch("app.main.stop_scheduler") as mock_stop_scheduler, \
         patch("app.main.close_pool") as mock_close_pool, \
         patch("app.main.close_redis") as mock_close_redis, \
         patch("app.main.engine") as mock_engine, \
         patch("app.main._shutdown_timeout", 0.1):  # 设置很短的超时时间

        # 模拟慢速关闭（超过超时时间）
        async def slow_stop():
            await asyncio.sleep(1)  # 睡眠 1 秒，超过 0.1 秒超时

        mock_stop_scheduler.side_effect = slow_stop
        mock_close_pool.return_value = AsyncMock()()
        mock_close_redis.return_value = AsyncMock()()
        mock_engine.dispose = AsyncMock()

        from app.main import _graceful_shutdown

        # 执行优雅关闭（应该触发超时）
        await _graceful_shutdown()

        # 验证 stop_scheduler 被调用了两次（第一次超时，第二次强制停止）
        assert mock_stop_scheduler.call_count == 2
        mock_close_pool.assert_called_once()
        mock_close_redis.assert_called_once()
        mock_engine.dispose.assert_called_once()


def test_signal_handler_sigterm():
    """测试信号处理器 - SIGTERM。"""
    with patch("app.main._shutdown_event") as mock_event:
        from app.main import _handle_shutdown_signal

        # 模拟接收 SIGTERM 信号
        _handle_shutdown_signal(signal.SIGTERM, None)

        # 验证关闭事件被设置
        mock_event.set.assert_called_once()


def test_signal_handler_sigint():
    """测试信号处理器 - SIGINT。"""
    with patch("app.main._shutdown_event") as mock_event:
        from app.main import _handle_shutdown_signal

        # 模拟接收 SIGINT 信号
        _handle_shutdown_signal(signal.SIGINT, None)

        # 验证关闭事件被设置
        mock_event.set.assert_called_once()


def test_setup_signal_handlers():
    """测试信号处理器设置。"""
    with patch("signal.signal") as mock_signal:
        from app.main import _setup_signal_handlers

        # 设置信号处理器
        _setup_signal_handlers()

        # 验证 SIGTERM 和 SIGINT 都被设置
        assert mock_signal.call_count == 2
        calls = mock_signal.call_args_list
        signal_nums = [call[0][0] for call in calls]
        assert signal.SIGTERM in signal_nums
        assert signal.SIGINT in signal_nums
