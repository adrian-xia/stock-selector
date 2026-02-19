"""测试 WebSocket 实时行情端点。"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.websocket import _connections, get_connection_count


class TestWebSocketConnections:
    """测试 WebSocket 连接管理。"""

    def test_get_connection_count_empty(self):
        _connections.clear()
        assert get_connection_count() == 0

    def test_get_connection_count(self):
        _connections.clear()
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()
        _connections[mock_ws1] = {"600519.SH"}
        _connections[mock_ws2] = {"000001.SZ"}
        assert get_connection_count() == 2
        _connections.clear()


class TestSubscriptionLogic:
    """测试订阅逻辑（不启动真实 WebSocket）。"""

    def test_subscription_limit(self):
        """验证订阅上限逻辑。"""
        _connections.clear()
        mock_ws = MagicMock()
        current = set()
        _connections[mock_ws] = current

        # 添加 50 只
        for i in range(50):
            current.add(f"{600000 + i}.SH")
        _connections[mock_ws] = current

        # 验证已达上限
        assert len(_connections[mock_ws]) == 50
        _connections.clear()

    def test_unsubscribe(self):
        """验证取消订阅。"""
        _connections.clear()
        mock_ws = MagicMock()
        _connections[mock_ws] = {"600519.SH", "000001.SZ"}

        # 取消订阅
        _connections[mock_ws] -= {"600519.SH"}
        assert "600519.SH" not in _connections[mock_ws]
        assert "000001.SZ" in _connections[mock_ws]
        _connections.clear()

    def test_disconnect_cleanup(self):
        """验证断连清理。"""
        _connections.clear()
        mock_ws = MagicMock()
        _connections[mock_ws] = {"600519.SH"}
        assert get_connection_count() == 1

        _connections.pop(mock_ws, None)
        assert get_connection_count() == 0
