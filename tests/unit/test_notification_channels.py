"""测试通知渠道：企业微信、Telegram。"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.notification import WeComChannel, TelegramChannel, NotificationManager


class TestWeComChannel:
    """测试企业微信 Webhook 渠道。"""

    @pytest.mark.asyncio
    async def test_send_success(self):
        channel = WeComChannel("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("app.notification.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            result = await channel.send("测试标题", "测试消息")
        assert result is True
        mock_client.post.assert_called_once()
        payload = mock_client.post.call_args[1]["json"]
        assert payload["msgtype"] == "markdown"
        assert "测试标题" in payload["markdown"]["content"]

    @pytest.mark.asyncio
    async def test_send_failure(self):
        channel = WeComChannel("https://example.com/webhook")
        with patch("app.notification.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("timeout"))
            mock_client_cls.return_value = mock_client
            result = await channel.send("标题", "消息")
        assert result is False


class TestTelegramChannel:
    """测试 Telegram Bot API 渠道。"""

    @pytest.mark.asyncio
    async def test_send_success(self):
        channel = TelegramChannel("bot123:token", "chat456")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("app.notification.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            result = await channel.send("测试标题", "测试消息")
        assert result is True
        payload = mock_client.post.call_args[1]["json"]
        assert payload["chat_id"] == "chat456"
        assert payload["parse_mode"] == "Markdown"
        assert "测试标题" in payload["text"]

    @pytest.mark.asyncio
    async def test_send_failure(self):
        channel = TelegramChannel("bot123:token", "chat456")
        with patch("app.notification.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("network error"))
            mock_client_cls.return_value = mock_client
            result = await channel.send("标题", "消息")
        assert result is False
