"""测试任务状态管理模块。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.scheduler.state import SyncState, SyncStateManager


@pytest.mark.asyncio
async def test_state_flow():
    """测试状态流转（pending → probing → syncing → completed）。"""
    # 模拟 Redis 客户端
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # 初始状态为 None
    mock_redis.set = AsyncMock()

    manager = SyncStateManager(mock_redis)
    target = date(2026, 2, 10)

    # 初始状态应为 PENDING
    state = await manager.get_state(target)
    assert state == SyncState.PENDING

    # 设置状态为 PROBING
    await manager.set_state(target, SyncState.PROBING)
    mock_redis.set.assert_called_once()

    # 模拟 Redis 返回 PROBING
    mock_redis.get.return_value = b"probing"
    state = await manager.get_state(target)
    assert state == SyncState.PROBING

    # 设置状态为 SYNCING
    mock_redis.set.reset_mock()
    await manager.set_state(target, SyncState.SYNCING)
    mock_redis.set.assert_called_once()

    # 模拟 Redis 返回 SYNCING
    mock_redis.get.return_value = b"syncing"
    state = await manager.get_state(target)
    assert state == SyncState.SYNCING

    # 设置状态为 COMPLETED
    mock_redis.set.reset_mock()
    await manager.set_state(target, SyncState.COMPLETED)
    mock_redis.set.assert_called_once()

    # 模拟 Redis 返回 COMPLETED
    mock_redis.get.return_value = b"completed"
    state = await manager.get_state(target)
    assert state == SyncState.COMPLETED


@pytest.mark.asyncio
async def test_is_completed():
    """测试任务是否已完成。"""
    # 模拟 Redis 客户端
    mock_redis = AsyncMock()
    manager = SyncStateManager(mock_redis)
    target = date(2026, 2, 10)

    # 状态为 COMPLETED
    mock_redis.get.return_value = b"completed"
    result = await manager.is_completed(target)
    assert result is True

    # 状态为 PROBING
    mock_redis.get.return_value = b"probing"
    result = await manager.is_completed(target)
    assert result is False

    # 状态为 None
    mock_redis.get.return_value = None
    result = await manager.is_completed(target)
    assert result is False


@pytest.mark.asyncio
async def test_increment_probe_count():
    """测试嗅探计数递增。"""
    # 模拟 Redis 客户端
    mock_redis = AsyncMock()
    mock_redis.incr.side_effect = [1, 2, 3]  # 模拟递增返回值
    mock_redis.expire = AsyncMock()

    manager = SyncStateManager(mock_redis)
    target = date(2026, 2, 10)

    # 第一次递增
    count = await manager.increment_probe_count(target)
    assert count == 1
    mock_redis.incr.assert_called_once()
    mock_redis.expire.assert_called_once()  # 首次创建时设置 TTL

    # 第二次递增
    mock_redis.expire.reset_mock()
    count = await manager.increment_probe_count(target)
    assert count == 2
    mock_redis.expire.assert_not_called()  # 非首次不设置 TTL

    # 第三次递增
    count = await manager.increment_probe_count(target)
    assert count == 3


@pytest.mark.asyncio
async def test_probe_job_id_storage():
    """测试任务 ID 存储和获取。"""
    # 模拟 Redis 客户端
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.get.return_value = b"probe_and_sync_2026-02-10"

    manager = SyncStateManager(mock_redis)
    target = date(2026, 2, 10)
    job_id = "probe_and_sync_2026-02-10"

    # 保存任务 ID
    await manager.save_probe_job_id(target, job_id)
    mock_redis.set.assert_called_once()

    # 获取任务 ID
    retrieved_id = await manager.get_probe_job_id(target)
    assert retrieved_id == job_id
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_redis_unavailable():
    """测试 Redis 不可用时的降级行为。"""
    manager = SyncStateManager(None)  # Redis 不可用
    target = date(2026, 2, 10)

    # 获取状态应返回 PENDING
    state = await manager.get_state(target)
    assert state == SyncState.PENDING

    # 设置状态不应报错
    await manager.set_state(target, SyncState.PROBING)

    # 检查是否完成应返回 False
    result = await manager.is_completed(target)
    assert result is False

    # 递增计数应返回 0
    count = await manager.increment_probe_count(target)
    assert count == 0

    # 保存任务 ID 不应报错
    await manager.save_probe_job_id(target, "test_job_id")

    # 获取任务 ID 应返回 None
    job_id = await manager.get_probe_job_id(target)
    assert job_id is None
