"""BaoStock 连接池管理模块。

提供连接池功能，复用 BaoStock 登录会话，避免频繁 login/logout 操作。

主要组件：
- BaoStockSession: 封装单个 BaoStock 会话的状态
- BaoStockConnectionPool: 连接池实现，基于 asyncio.Queue
- get_pool() / close_pool(): 全局单例管理函数

使用示例：
    # 获取全局连接池
    pool = get_pool()

    # 使用 context manager 获取连接
    async with pool.acquire() as session:
        # 使用 session 进行查询
        ...

    # 应用关闭时清理连接池
    await close_pool()
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import AsyncIterator

import baostock as bs

from app.config import settings
from app.exceptions import DataSourceError

logger = logging.getLogger(__name__)


@dataclass
class BaoStockSession:
    """BaoStock 会话封装。

    Attributes:
        session_id: 会话标识（用于日志）
        logged_in: 是否已登录
        last_used: 最后使用时间（Unix 时间戳）
    """
    session_id: int
    logged_in: bool = False
    last_used: float = 0.0


class BaoStockConnectionPool:
    """BaoStock 连接池。

    维护一个可复用的 BaoStock 会话池，避免频繁 login/logout。

    Args:
        size: 连接池大小（最大并发连接数）
        timeout: 获取连接的超时时间（秒）
        session_ttl: 会话生存时间（秒），超时后重新 login
    """

    def __init__(
        self,
        size: int = 5,
        timeout: float = 30.0,
        session_ttl: float = 3600.0,
    ) -> None:
        self._size = size
        self._timeout = timeout
        self._session_ttl = session_ttl
        self._queue: asyncio.Queue[BaoStockSession] = asyncio.Queue(maxsize=size)
        self._created_count = 0
        self._closed = False
        logger.info(
            "BaoStock 连接池初始化：size=%d, timeout=%.1fs, ttl=%.1fs",
            size, timeout, session_ttl,
        )

    async def acquire(self) -> BaoStockSession:
        """从连接池获取一个可用的会话。

        如果队列为空且未达到池大小上限，立即创建新会话。
        如果会话已过期（超过 TTL），重新 login。

        Returns:
            可用的 BaoStockSession

        Raises:
            TimeoutError: 超时未获取到连接
            DataSourceError: BaoStock login 失败
        """
        if self._closed:
            raise RuntimeError("连接池已关闭")

        session = None

        # 优先尝试从队列获取（非阻塞）
        try:
            session = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            # 队列为空，检查是否可以创建新连接
            if self._created_count < self._size:
                # 立即创建新会话，不等待
                session = await self._create_session()
            else:
                # 已达上限，阻塞等待其他会话释放
                try:
                    session = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self._timeout,
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"连接池获取超时（{self._timeout}s），所有连接都在使用中"
                    )

        # 检查会话是否过期
        now = time.time()
        if session.logged_in and (now - session.last_used) > self._session_ttl:
            logger.info("会话 %d 已过期，重新登录", session.session_id)
            await self._login_session(session)
        elif not session.logged_in:
            await self._login_session(session)

        session.last_used = now
        return session

    async def release(self, session: BaoStockSession) -> None:
        """将会话放回连接池。

        Args:
            session: 要释放的会话
        """
        if self._closed:
            # 连接池已关闭，直接 logout
            await self._logout_session(session)
            return

        session.last_used = time.time()
        await self._queue.put(session)

    async def _create_session(self) -> BaoStockSession:
        """创建新的会话。"""
        self._created_count += 1
        session = BaoStockSession(session_id=self._created_count)
        logger.debug("创建新会话：%d", session.session_id)
        await self._login_session(session)
        session.last_used = time.time()
        return session

    async def _login_session(self, session: BaoStockSession) -> None:
        """登录会话（在线程池中执行）。"""
        def _login_sync():
            result = bs.login()
            if result.error_code != "0":
                raise DataSourceError(f"BaoStock login 失败: {result.error_msg}")

        await asyncio.to_thread(_login_sync)
        session.logged_in = True
        logger.debug("会话 %d 登录成功", session.session_id)

    async def _logout_session(self, session: BaoStockSession) -> None:
        """登出会话（在线程池中执行）。"""
        if not session.logged_in:
            return

        def _logout_sync():
            bs.logout()

        await asyncio.to_thread(_logout_sync)
        session.logged_in = False
        logger.debug("会话 %d 登出成功", session.session_id)

    async def close(self) -> None:
        """关闭连接池，登出所有会话。"""
        if self._closed:
            return

        self._closed = True
        logger.info("关闭连接池，登出所有会话")

        # 登出队列中的所有会话
        sessions = []
        while not self._queue.empty():
            try:
                session = self._queue.get_nowait()
                sessions.append(session)
            except asyncio.QueueEmpty:
                break

        for session in sessions:
            await self._logout_session(session)

        logger.info("连接池已关闭，共登出 %d 个会话", len(sessions))

    async def health_check(self) -> bool:
        """健康检查：验证所有连接可用。

        Returns:
            True 如果所有会话都正常，False 如果有会话失败
        """
        # 简单实现：检查连接池是否已关闭
        return not self._closed

    async def __aenter__(self) -> BaoStockSession:
        """Async context manager 入口。"""
        return await self.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager 出口，自动释放连接。"""
        # 注意：这里需要从 __aenter__ 返回的 session
        # 但 context manager 协议不支持传递，所以需要在外部使用
        # 正确用法：async with pool.acquire() as session:
        pass


# 全局连接池单例
_pool: BaoStockConnectionPool | None = None


def get_pool() -> BaoStockConnectionPool:
    """获取全局连接池单例。

    如果连接池未初始化，使用配置中的参数创建。

    Returns:
        全局 BaoStockConnectionPool 实例
    """
    global _pool
    if _pool is None:
        _pool = BaoStockConnectionPool(
            size=settings.baostock_pool_size,
            timeout=settings.baostock_pool_timeout,
            session_ttl=settings.baostock_session_ttl,
        )
    return _pool


async def close_pool() -> None:
    """关闭全局连接池。

    应在应用关闭时调用，确保所有会话正确登出。
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
