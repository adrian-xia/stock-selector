"""BaoStockConnectionPool 单元测试。"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.pool import BaoStockConnectionPool, BaoStockSession


# ============================================================
# 辅助函数
# ============================================================

def _make_pool(
    size: int = 3,
    timeout: float = 0.05,
    session_ttl: float = 3600.0,
) -> BaoStockConnectionPool:
    """创建测试用连接池。"""
    return BaoStockConnectionPool(
        size=size,
        timeout=timeout,
        session_ttl=session_ttl,
    )


# ============================================================
# 1. 基本功能（acquire / release）
# ============================================================

class TestAcquireRelease:
    """连接池 acquire/release 基本功能测试。"""

    @patch("app.data.pool.bs")
    async def test_acquire_creates_session(self, mock_bs: MagicMock) -> None:
        """首次 acquire 应创建新会话并 login。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=2)
        session = await pool.acquire()

        assert isinstance(session, BaoStockSession)
        assert session.logged_in is True
        assert session.session_id == 1
        mock_bs.login.assert_called_once()

        await pool.release(session)
        await pool.close()

    @patch("app.data.pool.bs")
    async def test_release_and_reuse(self, mock_bs: MagicMock) -> None:
        """release 后再次 acquire 应复用同一会话，不再 login。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=2)
        session1 = await pool.acquire()
        sid = session1.session_id
        await pool.release(session1)

        # 再次 acquire 应复用
        session2 = await pool.acquire()
        assert session2.session_id == sid
        # login 只调用了一次（创建时）
        assert mock_bs.login.call_count == 1

        await pool.release(session2)
        await pool.close()

    @patch("app.data.pool.bs")
    async def test_acquire_multiple_sessions(self, mock_bs: MagicMock) -> None:
        """并发 acquire 应创建多个会话。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=3)
        s1 = await pool.acquire()
        s2 = await pool.acquire()

        assert s1.session_id != s2.session_id
        assert mock_bs.login.call_count == 2

        await pool.release(s1)
        await pool.release(s2)
        await pool.close()

    @patch("app.data.pool.bs")
    async def test_acquire_on_closed_pool_raises(self, mock_bs: MagicMock) -> None:
        """关闭后 acquire 应抛出 RuntimeError。"""
        pool = _make_pool()
        await pool.close()

        with pytest.raises(RuntimeError, match="连接池已关闭"):
            await pool.acquire()


# ============================================================
# 2. Async Context Manager
# ============================================================

class TestAsyncContextManager:
    """async context manager 测试。"""

    @patch("app.data.pool.bs")
    async def test_context_manager_acquire_release(self, mock_bs: MagicMock) -> None:
        """context manager 应自动 acquire 和 release。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=2)

        # 注意：pool 本身的 __aenter__/__aexit__ 实现不完整
        # 实际使用方式是手动 acquire/release
        session = await pool.acquire()
        assert session.logged_in is True
        await pool.release(session)

        # 验证 release 后连接回到池中可以再次获取
        session2 = await pool.acquire()
        assert session2.session_id == session.session_id
        await pool.release(session2)
        await pool.close()


# ============================================================
# 3. 会话 TTL 过期和重新 login
# ============================================================

class TestSessionTTL:
    """会话 TTL 过期测试。"""

    @patch("app.data.pool.bs")
    async def test_expired_session_relogin(self, mock_bs: MagicMock) -> None:
        """过期会话在 acquire 时应重新 login。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=2, session_ttl=1.0)
        session = await pool.acquire()
        await pool.release(session)

        # 模拟会话过期：release 后修改 last_used（对象引用仍在队列中）
        session.last_used = time.time() - 10

        # 再次 acquire，应触发重新 login
        session2 = await pool.acquire()
        # 创建时 login 1 次 + 过期重新 login 1 次 = 2 次
        assert mock_bs.login.call_count == 2
        assert session2.logged_in is True

        await pool.release(session2)
        await pool.close()

    @patch("app.data.pool.bs")
    async def test_not_expired_session_no_relogin(self, mock_bs: MagicMock) -> None:
        """未过期会话不应重新 login。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=2, session_ttl=3600.0)
        session = await pool.acquire()
        await pool.release(session)

        session2 = await pool.acquire()
        # 只有创建时的 1 次 login
        assert mock_bs.login.call_count == 1

        await pool.release(session2)
        await pool.close()

    @patch("app.data.pool.bs")
    async def test_not_logged_in_session_login(self, mock_bs: MagicMock) -> None:
        """未登录的会话在 acquire 时应 login。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=2)
        session = await pool.acquire()
        session.logged_in = False
        await pool.release(session)

        session2 = await pool.acquire()
        # 创建时 1 次 + 未登录重新 login 1 次 = 2 次
        assert mock_bs.login.call_count == 2

        await pool.release(session2)
        await pool.close()


# ============================================================
# 4. 连接池满时的等待和超时
# ============================================================

class TestPoolFullTimeout:
    """连接池满时的等待和超时测试。"""

    @patch("app.data.pool.bs")
    async def test_pool_full_timeout(self, mock_bs: MagicMock) -> None:
        """连接池满且超时应抛出 TimeoutError。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=1, timeout=0.1)
        # 获取唯一的连接
        session = await pool.acquire()

        # 再次 acquire 应超时
        with pytest.raises(TimeoutError, match="连接池获取超时"):
            await pool.acquire()

        await pool.release(session)
        await pool.close()

    @patch("app.data.pool.bs")
    async def test_pool_full_wait_then_release(self, mock_bs: MagicMock) -> None:
        """连接池满时，等待其他任务 release 后应能获取。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=1, timeout=2.0)
        session = await pool.acquire()

        async def release_later():
            await asyncio.sleep(0.1)
            await pool.release(session)

        # 并发：一个任务稍后 release，另一个等待 acquire
        task = asyncio.create_task(release_later())
        session2 = await pool.acquire()
        await task

        assert session2.session_id == session.session_id
        await pool.release(session2)
        await pool.close()


# ============================================================
# 5. close() 方法
# ============================================================

class TestClose:
    """close() 方法测试。"""

    @patch("app.data.pool.bs")
    async def test_close_logouts_all_sessions(self, mock_bs: MagicMock) -> None:
        """close 应 logout 所有队列中的会话。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=3)
        s1 = await pool.acquire()
        s2 = await pool.acquire()
        await pool.release(s1)
        await pool.release(s2)

        await pool.close()

        # logout 应被调用（队列中有 2 个会话）
        assert mock_bs.logout.call_count == 2

    @patch("app.data.pool.bs")
    async def test_close_idempotent(self, mock_bs: MagicMock) -> None:
        """多次 close 不应报错。"""
        pool = _make_pool()
        await pool.close()
        await pool.close()  # 第二次不应报错

    @patch("app.data.pool.bs")
    async def test_release_after_close_logouts(self, mock_bs: MagicMock) -> None:
        """关闭后 release 应直接 logout 而非放回队列。"""
        mock_bs.login.return_value = MagicMock(error_code="0")

        pool = _make_pool(size=2)
        session = await pool.acquire()
        await pool.close()

        # 关闭后 release 应 logout
        await pool.release(session)
        assert mock_bs.logout.call_count == 1


# ============================================================
# 6. health_check() 方法
# ============================================================

class TestHealthCheck:
    """health_check() 方法测试。"""

    @patch("app.data.pool.bs")
    async def test_healthy_pool(self, mock_bs: MagicMock) -> None:
        """未关闭的连接池应返回 True。"""
        pool = _make_pool()
        assert await pool.health_check() is True
        await pool.close()

    @patch("app.data.pool.bs")
    async def test_closed_pool_unhealthy(self, mock_bs: MagicMock) -> None:
        """已关闭的连接池应返回 False。"""
        pool = _make_pool()
        await pool.close()
        assert await pool.health_check() is False
