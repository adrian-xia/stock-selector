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
        self._base_url = f"https://api.telegram.org/bot{bot_token}"
        self._chat_id = chat_id

    async def send(self, title: str, message: str) -> bool:
        """发送 Telegram 文本消息。"""
        text = f"*{title}*\n{message}"
        payload = {"chat_id": self._chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{self._base_url}/sendMessage", json=payload)
                return resp.status_code == 200
        except Exception:
            logger.warning("[TelegramChannel] 发送失败", exc_info=True)
            return False

    async def send_document(self, filename: str, content: bytes, caption: str = "") -> bool:
        """发送 Telegram 文件附件（multipart 上传）。

        Args:
            filename: 文件名（如 post_market_2026-02-28.md）
            content: 文件内容字节
            caption: 文件说明文字
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._base_url}/sendDocument",
                    data={"chat_id": self._chat_id, "caption": caption},
                    files={"document": (filename, content, "text/markdown")},
                )
                return resp.status_code == 200
        except Exception:
            logger.warning("[TelegramChannel] 文件发送失败: %s", filename, exc_info=True)
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

    async def send_report(
        self,
        title: str,
        summary_text: str,
        markdown_content: str,
        filename: str,
    ) -> None:
        """发送报告：先发摘要文本，再发 Markdown 文件附件。

        Args:
            title: 通知标题
            summary_text: 简短摘要（文本消息）
            markdown_content: 完整报告内容（作为 .md 文件发送）
            filename: 附件文件名
        """
        # 1. 发摘要文本
        await self.send(NotificationLevel.INFO, title, summary_text)

        # 2. 发文件附件（仅 Telegram 支持）
        content_bytes = markdown_content.encode("utf-8")
        for channel in self._channels:
            if isinstance(channel, TelegramChannel):
                try:
                    await channel.send_document(filename, content_bytes, caption=title)
                except Exception:
                    logger.warning("[NotificationManager] 文件发送失败: %s", filename, exc_info=True)

