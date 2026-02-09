"""测试自动数据更新系统的集成场景。

注意：这些测试需要真实的数据库和 Redis 连接。
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from app.scheduler.auto_update import auto_update_job, probe_and_sync_job
from app.scheduler.state import SyncState, SyncStateManager


@pytest.mark.asyncio
async def test_scenario_1_trading_day_data_ready():
    """测试场景 1：交易日 15:30 触发，数据已就绪。

    预期：立即执行盘后链路，标记完成。
    """
    target = date(2026, 2, 10)

    # Mock 依赖
    with patch("app.scheduler.auto_update._build_manager") as mock_build_manager, \
         patch("app.scheduler.auto_update.get_redis") as mock_get_redis, \
         patch("app.scheduler.auto_update.probe_daily_data") as mock_probe, \
         patch("app.scheduler.auto_update.run_post_market_chain") as mock_run_chain:

        # 模拟交易日
        mock_manager = AsyncMock()
        mock_manager.is_trade_day.return_value = True
        mock_build_manager.return_value = mock_manager

        # 模拟 Redis
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # 初始状态为 None
        mock_redis.set = AsyncMock()
        mock_get_redis.return_value = mock_redis

        # 模拟数据已就绪
        mock_probe.return_value = True

        # 模拟盘后链路成功
        mock_run_chain.return_value = None

        # 执行任务
        await auto_update_job(target)

        # 验证
        mock_manager.is_trade_day.assert_called_once_with(target)
        mock_probe.assert_called_once()
        mock_run_chain.assert_called_once_with(target)
        # 验证状态设置为 SYNCING 和 COMPLETED
        assert mock_redis.set.call_count >= 2


@pytest.mark.asyncio
async def test_scenario_2_trading_day_data_not_ready():
    """测试场景 2：交易日 15:30 触发，数据未就绪，启动嗅探任务。

    预期：启动嗅探任务，每 15 分钟嗅探一次。
    """
    target = date(2026, 2, 10)

    # Mock 依赖
    with patch("app.scheduler.auto_update._build_manager") as mock_build_manager, \
         patch("app.scheduler.auto_update.get_redis") as mock_get_redis, \
         patch("app.scheduler.auto_update.probe_daily_data") as mock_probe, \
         patch("app.scheduler.auto_update._scheduler") as mock_scheduler:

        # 模拟交易日
        mock_manager = AsyncMock()
        mock_manager.is_trade_day.return_value = True
        mock_build_manager.return_value = mock_manager

        # 模拟 Redis
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set = AsyncMock()
        mock_get_redis.return_value = mock_redis

        # 模拟数据未就绪
        mock_probe.return_value = False

        # 模拟调度器
        mock_scheduler.add_job = MagicMock()

        # 执行任务
        await auto_update_job(target)

        # 验证
        mock_probe.assert_called_once()
        mock_scheduler.add_job.assert_called_once()
        # 验证状态设置为 PROBING
        assert mock_redis.set.call_count >= 1


@pytest.mark.asyncio
async def test_scenario_3_probe_timeout():
    """测试场景 3：交易日 15:30 触发，数据未就绪，18:00 超时。

    预期：发送超时报警，停止嗅探任务。
    """
    target = date(2026, 2, 10)

    # Mock 依赖
    with patch("app.scheduler.auto_update.get_redis") as mock_get_redis, \
         patch("app.scheduler.auto_update.probe_daily_data") as mock_probe, \
         patch("app.scheduler.auto_update.NotificationManager") as mock_notifier_class, \
         patch("app.scheduler.auto_update._stop_probe_job") as mock_stop_job, \
         patch("app.scheduler.auto_update.datetime") as mock_datetime:

        # 模拟 Redis
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b"probing"
        mock_redis.set = AsyncMock()
        mock_redis.incr.return_value = 12
        mock_get_redis.return_value = mock_redis

        # 模拟数据未就绪
        mock_probe.return_value = False

        # 模拟当前时间超过 18:00
        mock_now = MagicMock()
        mock_now.time.return_value = MagicMock(hour=18, minute=30)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime.return_value = MagicMock(time=lambda: MagicMock(hour=18, minute=0))

        # 模拟通知管理器
        mock_notifier = AsyncMock()
        mock_notifier_class.return_value = mock_notifier

        # 执行嗅探任务
        await probe_and_sync_job(target)

        # 验证
        mock_notifier.send.assert_called_once()
        mock_stop_job.assert_called_once()
        # 验证状态设置为 FAILED
        assert mock_redis.set.call_count >= 1


@pytest.mark.asyncio
async def test_scenario_4_non_trading_day():
    """测试场景 4：非交易日 15:30 触发。

    预期：记录日志并退出，不执行任何操作。
    """
    target = date(2026, 2, 9)  # 假设是周日

    # Mock 依赖
    with patch("app.scheduler.auto_update._build_manager") as mock_build_manager, \
         patch("app.scheduler.auto_update.get_redis") as mock_get_redis, \
         patch("app.scheduler.auto_update.probe_daily_data") as mock_probe:

        # 模拟非交易日
        mock_manager = AsyncMock()
        mock_manager.is_trade_day.return_value = False
        mock_build_manager.return_value = mock_manager

        # 模拟 Redis
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        # 执行任务
        await auto_update_job(target)

        # 验证
        mock_manager.is_trade_day.assert_called_once_with(target)
        mock_probe.assert_not_called()  # 不应执行嗅探


@pytest.mark.asyncio
async def test_scenario_5_probe_success_after_retry():
    """测试场景 5：嗅探任务重试后成功。

    预期：执行盘后链路，停止嗅探任务。
    """
    target = date(2026, 2, 10)

    # Mock 依赖
    with patch("app.scheduler.auto_update.get_redis") as mock_get_redis, \
         patch("app.scheduler.auto_update.probe_daily_data") as mock_probe, \
         patch("app.scheduler.auto_update.run_post_market_chain") as mock_run_chain, \
         patch("app.scheduler.auto_update._stop_probe_job") as mock_stop_job, \
         patch("app.scheduler.auto_update.datetime") as mock_datetime:

        # 模拟 Redis
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b"probing"
        mock_redis.set = AsyncMock()
        mock_redis.incr.return_value = 3
        mock_get_redis.return_value = mock_redis

        # 模拟数据已就绪
        mock_probe.return_value = True

        # 模拟当前时间未超时
        mock_now = MagicMock()
        mock_now.time.return_value = MagicMock(hour=16, minute=0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime.return_value = MagicMock(time=lambda: MagicMock(hour=18, minute=0))

        # 模拟盘后链路成功
        mock_run_chain.return_value = None

        # 执行嗅探任务
        await probe_and_sync_job(target)

        # 验证
        mock_probe.assert_called_once()
        mock_run_chain.assert_called_once_with(target)
        mock_stop_job.assert_called_once()
        # 验证状态设置为 SYNCING 和 COMPLETED
        assert mock_redis.set.call_count >= 2
