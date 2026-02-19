"""实时监控管理器：统一管理采集生命周期。"""

import logging

from app.realtime.collector import RealtimeCollector
from app.realtime.publisher import RealtimePublisher

logger = logging.getLogger(__name__)


class RealtimeManager:
    """统一管理实时行情采集的生命周期（start/stop）。

    交易时段自动启停由 collector 内部的 is_trading_hours 判断控制。
    """

    def __init__(self, tushare_client, redis_client=None):
        self._publisher = RealtimePublisher(redis_client) if redis_client else None
        self._collector = RealtimeCollector(tushare_client, self._publisher)

    @property
    def collector(self) -> RealtimeCollector:
        return self._collector

    @property
    def is_running(self) -> bool:
        return self._collector.is_running

    @property
    def watchlist_count(self) -> int:
        return len(self._collector.watchlist)

    async def start(self) -> None:
        """启动实时监控。"""
        await self._collector.start()
        logger.info("[RealtimeManager] 实时监控已启动")

    async def stop(self) -> None:
        """停止实时监控。"""
        await self._collector.stop()
        logger.info("[RealtimeManager] 实时监控已停止")
