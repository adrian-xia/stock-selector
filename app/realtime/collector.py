"""实时行情采集器：基于 TushareClient 定时轮询盘中行情。"""

import asyncio
import logging
from datetime import datetime, time

from app.config import settings

logger = logging.getLogger(__name__)

# A 股交易时段
TRADING_START = time(9, 15)
TRADING_END = time(15, 0)


def is_trading_hours(now: datetime | None = None) -> bool:
    """判断当前是否在交易时段（9:15-15:00）。"""
    now = now or datetime.now()
    current_time = now.time()
    return TRADING_START <= current_time <= TRADING_END


class RealtimeCollector:
    """实时行情采集器。

    通过 TushareClient 定时轮询监控股票的实时行情，
    连续失败 3 次暂停 1 分钟后重试。
    """

    def __init__(self, tushare_client, publisher=None):
        self._client = tushare_client
        self._publisher = publisher
        self._watchlist: set[str] = set()
        self._running = False
        self._task: asyncio.Task | None = None
        self._consecutive_failures = 0
        self._max_failures = 3
        self._pause_seconds = 60

    @property
    def watchlist(self) -> set[str]:
        return self._watchlist.copy()

    @property
    def is_running(self) -> bool:
        return self._running

    def add_stock(self, ts_code: str) -> bool:
        """添加监控股票，超过上限返回 False。"""
        if len(self._watchlist) >= settings.realtime_max_stocks:
            return False
        self._watchlist.add(ts_code)
        return True

    def remove_stock(self, ts_code: str) -> None:
        """移除监控股票。"""
        self._watchlist.discard(ts_code)

    async def start(self) -> None:
        """启动采集循环。"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("[RealtimeCollector] 采集启动")

    async def stop(self) -> None:
        """停止采集循环。"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[RealtimeCollector] 采集停止")

    async def _poll_loop(self) -> None:
        """轮询主循环。"""
        while self._running:
            try:
                if not is_trading_hours():
                    await asyncio.sleep(settings.realtime_poll_interval)
                    continue

                if not self._watchlist:
                    await asyncio.sleep(settings.realtime_poll_interval)
                    continue

                await self._fetch_and_publish()
                self._consecutive_failures = 0

            except asyncio.CancelledError:
                break
            except Exception:
                self._consecutive_failures += 1
                logger.warning(
                    "[RealtimeCollector] 采集失败 (%d/%d)\n",
                    self._consecutive_failures,
                    self._max_failures,
                    exc_info=True,
                )
                if self._consecutive_failures >= self._max_failures:
                    logger.warning("[RealtimeCollector] 连续失败 %d 次，暂停 %d 秒", self._max_failures, self._pause_seconds)
                    await asyncio.sleep(self._pause_seconds)
                    self._consecutive_failures = 0

            await asyncio.sleep(settings.realtime_poll_interval)

    async def _fetch_and_publish(self) -> None:
        """获取实时行情并发布到 Redis。"""
        ts_codes = list(self._watchlist)
        # 使用 Tushare realtime_quote 或 daily 当日数据
        # 按逗号拼接股票代码批量获取
        codes_str = ",".join(ts_codes)
        try:
            raw_data = await self._client.fetch_realtime_quote(ts_codes=codes_str)
        except AttributeError:
            # fallback: 如果 TushareClient 没有 fetch_realtime_quote，用 daily 当日
            today_str = datetime.now().strftime("%Y%m%d")
            raw_data = await self._client.fetch_raw_daily(trade_date=today_str)

        if not raw_data:
            return

        # 发布到 Redis Pub/Sub
        if self._publisher:
            for record in raw_data:
                ts_code = record.get("ts_code", "")
                if ts_code in self._watchlist:
                    await self._publisher.publish(ts_code, record)

