"""Redis Pub/Sub 发布器：将实时行情数据发布到 Redis channel。"""

import json
import logging

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "market:realtime:"


class RealtimePublisher:
    """将实时行情数据发布到 Redis Pub/Sub channel。"""

    def __init__(self, redis_client):
        self._redis = redis_client

    async def publish(self, ts_code: str, data: dict) -> None:
        """发布行情数据到 channel market:realtime:{ts_code}。"""
        if not self._redis:
            return
        channel = f"{CHANNEL_PREFIX}{ts_code}"
        try:
            payload = json.dumps(data, ensure_ascii=False, default=str)
            await self._redis.publish(channel, payload)
        except Exception:
            logger.warning("[RealtimePublisher] 发布失败: %s", ts_code, exc_info=True)
