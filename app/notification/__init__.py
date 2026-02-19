"""通知报警模块：多渠道通知分发。

支持渠道：
- 日志（默认，始终启用）
- 企业微信 Webhook
- Telegram Bot API
"""

import logging
from enum import Enum
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationLevel(str, Enum):
    """通知级别枚举。"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class WeComChannel:
    """企业微信 Webhook 通知渠道。"""

    def __init__(self, webhook_url: str):
        self._url = webhook_url

    async def send(self, title: str, message: str) -> bool:
        """发送企业微信 markdown 消息。"""
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": f"### {title}\n{message}"},
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=payload)
                return resp.status_code == 200
        except Exception:
            logger.warning("[WeComChannel] 发送失败", exc_info=True)
            return False

class TelegramChannel:
    """Telegram Bot API 通知渠道。"""

    def __init__(self, bot_token: str, chat_id: str):
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._chat_id = chat_id

    async def send(self, title: str, message: str) -> bool:
        """发送 Telegram 消息。"""
        text = f"*{title}*\n{message}"
        payload = {"chat_id": self._chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self._url, json=payload)
                return resp.status_code == 200
        except Exception:
            logger.warning("[TelegramChannel] 发送失败", exc_info=True)
            return False


class NotificationManager:
    """通知管理器：根据配置自动注册可用渠道，遍历发送。"""

    def __init__(self):
        self._channels: list = []
        # 根据配置自动注册渠道
        if settings.wecom_webhook_url:
            self._channels.append(WeComChannel(settings.wecom_webhook_url))
            logger.info("[NotificationManager] 已注册企业微信渠道")
        if settings.telegram_bot_token and settings.telegram_chat_id:
            self._channels.append(TelegramChannel(settings.telegram_bot_token, settings.telegram_chat_id))
            logger.info("[NotificationManager] 已注册 Telegram 渠道")

    async def send(
        self,
        level: NotificationLevel | str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """发送通知到所有已注册渠道。失败记日志不重试。"""
        # 始终记录日志
        log_message = f"[通知报警] {title}: {message}"
        if metadata:
            log_message += f" | 元数据: {metadata}"

        level_str = level.value if isinstance(level, NotificationLevel) else level
        if level_str == "error":
            logger.error(log_message)
        elif level_str == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 遍历渠道发送（fire-and-forget，失败不重试）
        for channel in self._channels:
            try:
                await channel.send(title, message)
            except Exception:
                logger.warning("[NotificationManager] 渠道发送失败: %s", type(channel).__name__, exc_info=True)

