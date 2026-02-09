"""通知报警模块：发送数据同步失败或超时的报警通知。

V1 阶段仅记录日志，V2 可接入企业微信/钉钉/邮件/短信等通知服务。
"""

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class NotificationLevel(str, Enum):
    """通知级别枚举。"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误


class NotificationManager:
    """通知管理器（V1 暂存实现）。

    V1 阶段仅记录日志，不接入实际通知服务。
    V2 扩展点：
    - 企业微信：通过 Webhook 发送群消息
    - 钉钉：通过 Webhook 发送群消息
    - 邮件：通过 SMTP 发送邮件
    - 短信：通过短信网关发送短信
    """

    async def send(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """发送通知。

        V1 实现：仅记录日志
        V2 实现：根据配置调用实际通知服务

        Args:
            level: 通知级别（INFO/WARNING/ERROR）
            title: 通知标题
            message: 通知消息
            metadata: 附加元数据（可选）

        Examples:
            >>> manager = NotificationManager()
            >>> await manager.send(
            ...     level=NotificationLevel.ERROR,
            ...     title="数据同步超时",
            ...     message="2026-02-10 数据嗅探超时，18:00 仍无数据",
            ...     metadata={"date": "2026-02-10", "probe_count": 12},
            ... )
        """
        # V1 实现：记录日志
        log_message = f"[通知报警] {title}: {message}"
        if metadata:
            log_message += f" | 元数据: {metadata}"

        if level == NotificationLevel.ERROR:
            logger.error(log_message)
        elif level == NotificationLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # V2 扩展点：接入实际通知服务
        # 示例代码（V2 实现时取消注释）：
        #
        # if self._wechat_webhook:
        #     await self._send_wechat(title, message, metadata)
        #
        # if self._dingtalk_webhook:
        #     await self._send_dingtalk(title, message, metadata)
        #
        # if self._email_config:
        #     await self._send_email(title, message, metadata)

    # V2 扩展方法示例（暂未实现）：
    #
    # async def _send_wechat(
    #     self, title: str, message: str, metadata: dict[str, Any] | None
    # ) -> None:
    #     """发送企业微信通知。"""
    #     # 实现企业微信 Webhook 调用
    #     pass
    #
    # async def _send_dingtalk(
    #     self, title: str, message: str, metadata: dict[str, Any] | None
    # ) -> None:
    #     """发送钉钉通知。"""
    #     # 实现钉钉 Webhook 调用
    #     pass
    #
    # async def _send_email(
    #     self, title: str, message: str, metadata: dict[str, Any] | None
    # ) -> None:
    #     """发送邮件通知。"""
    #     # 实现 SMTP 邮件发送
    #     pass
