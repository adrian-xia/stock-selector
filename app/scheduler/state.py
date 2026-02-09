"""同步任务状态管理模块：基于 Redis 跟踪任务状态和进度。

使用 Redis 存储任务状态，避免重复执行和跟踪同步进度。
状态数据设置 TTL 自动过期，无需手动清理。
"""

import logging
from datetime import date
from enum import Enum

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class SyncState(str, Enum):
    """同步任务状态枚举。

    状态流转：
    pending → probing → syncing → completed
                     ↓
                  failed (超时或同步失败)
    """

    PENDING = "pending"  # 待处理
    PROBING = "probing"  # 嗅探中
    SYNCING = "syncing"  # 同步中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class SyncStateManager:
    """同步任务状态管理器（基于 Redis）。

    使用 Redis 存储任务状态，Key 设计：
    - sync_status:{date} - 任务状态
    - probe_count:{date} - 嗅探次数计数
    - probe_job_id:{date} - 嗅探任务 ID

    所有 Key 的 TTL 设置为 7 天，自动清理过期数据。
    """

    def __init__(self, redis_client: aioredis.Redis | None) -> None:
        """初始化状态管理器。

        Args:
            redis_client: Redis 异步客户端，None 表示 Redis 不可用（降级模式）
        """
        self._redis = redis_client
        self._ttl_seconds = 7 * 24 * 3600  # 7 天

    def _get_status_key(self, target_date: date) -> str:
        """获取状态 Key。"""
        return f"sync_status:{target_date.isoformat()}"

    def _get_count_key(self, target_date: date) -> str:
        """获取嗅探计数 Key。"""
        return f"probe_count:{target_date.isoformat()}"

    def _get_job_id_key(self, target_date: date) -> str:
        """获取嗅探任务 ID Key。"""
        return f"probe_job_id:{target_date.isoformat()}"

    async def get_state(self, target_date: date) -> SyncState:
        """获取任务状态。

        Args:
            target_date: 目标日期

        Returns:
            任务状态，Redis 不可用或无记录时返回 PENDING
        """
        if self._redis is None:
            return SyncState.PENDING

        try:
            key = self._get_status_key(target_date)
            value = await self._redis.get(key)
            if value is None:
                return SyncState.PENDING
            return SyncState(value.decode("utf-8"))
        except Exception as e:
            logger.warning("[状态管理] 获取状态失败：%s", e)
            return SyncState.PENDING

    async def set_state(self, target_date: date, state: SyncState) -> None:
        """设置任务状态。

        Args:
            target_date: 目标日期
            state: 任务状态
        """
        if self._redis is None:
            logger.debug("[状态管理] Redis 不可用，跳过状态设置")
            return

        try:
            key = self._get_status_key(target_date)
            await self._redis.set(key, state.value, ex=self._ttl_seconds)
            logger.debug("[状态管理] 设置状态：%s = %s", key, state.value)
        except Exception as e:
            logger.warning("[状态管理] 设置状态失败：%s", e)

    async def is_completed(self, target_date: date) -> bool:
        """检查任务是否已完成。

        Args:
            target_date: 目标日期

        Returns:
            True 表示任务已完成，False 表示未完成或状态未知
        """
        state = await self.get_state(target_date)
        return state == SyncState.COMPLETED

    async def increment_probe_count(self, target_date: date) -> int:
        """递增嗅探计数。

        Args:
            target_date: 目标日期

        Returns:
            递增后的计数值，Redis 不可用时返回 0
        """
        if self._redis is None:
            return 0

        try:
            key = self._get_count_key(target_date)
            count = await self._redis.incr(key)
            # 设置 TTL（仅在首次创建时）
            if count == 1:
                await self._redis.expire(key, self._ttl_seconds)
            logger.debug("[状态管理] 嗅探计数递增：%s = %d", key, count)
            return count
        except Exception as e:
            logger.warning("[状态管理] 递增嗅探计数失败：%s", e)
            return 0

    async def save_probe_job_id(self, target_date: date, job_id: str) -> None:
        """保存嗅探任务 ID。

        Args:
            target_date: 目标日期
            job_id: APScheduler 任务 ID
        """
        if self._redis is None:
            logger.debug("[状态管理] Redis 不可用，跳过任务 ID 保存")
            return

        try:
            key = self._get_job_id_key(target_date)
            await self._redis.set(key, job_id, ex=self._ttl_seconds)
            logger.debug("[状态管理] 保存任务 ID：%s = %s", key, job_id)
        except Exception as e:
            logger.warning("[状态管理] 保存任务 ID 失败：%s", e)

    async def get_probe_job_id(self, target_date: date) -> str | None:
        """获取嗅探任务 ID。

        Args:
            target_date: 目标日期

        Returns:
            任务 ID，Redis 不可用或无记录时返回 None
        """
        if self._redis is None:
            return None

        try:
            key = self._get_job_id_key(target_date)
            value = await self._redis.get(key)
            if value is None:
                return None
            return value.decode("utf-8")
        except Exception as e:
            logger.warning("[状态管理] 获取任务 ID 失败：%s", e)
            return None
