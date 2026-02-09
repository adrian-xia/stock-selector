"""测试通知报警模块。"""

import pytest
import logging
from unittest.mock import patch

from app.notification import NotificationLevel, NotificationManager


@pytest.mark.asyncio
async def test_send_error_notification():
    """测试发送 ERROR 级别通知。"""
    manager = NotificationManager()

    with patch("app.notification.logger") as mock_logger:
        await manager.send(
            level=NotificationLevel.ERROR,
            title="数据同步失败",
            message="2026-02-10 盘后链路执行失败",
            metadata={"date": "2026-02-10", "error": "Connection timeout"},
        )

        # 验证日志记录
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "数据同步失败" in call_args
        assert "2026-02-10 盘后链路执行失败" in call_args
        assert "元数据" in call_args


@pytest.mark.asyncio
async def test_send_warning_notification():
    """测试发送 WARNING 级别通知。"""
    manager = NotificationManager()

    with patch("app.notification.logger") as mock_logger:
        await manager.send(
            level=NotificationLevel.WARNING,
            title="数据嗅探超时",
            message="2026-02-10 数据嗅探超时，18:00 仍无数据",
            metadata={"date": "2026-02-10", "probe_count": 12},
        )

        # 验证日志记录
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "数据嗅探超时" in call_args
        assert "2026-02-10 数据嗅探超时，18:00 仍无数据" in call_args


@pytest.mark.asyncio
async def test_send_info_notification():
    """测试发送 INFO 级别通知。"""
    manager = NotificationManager()

    with patch("app.notification.logger") as mock_logger:
        await manager.send(
            level=NotificationLevel.INFO,
            title="数据同步成功",
            message="2026-02-10 数据同步完成",
        )

        # 验证日志记录
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "数据同步成功" in call_args
        assert "2026-02-10 数据同步完成" in call_args


@pytest.mark.asyncio
async def test_send_notification_without_metadata():
    """测试发送通知（不带元数据）。"""
    manager = NotificationManager()

    with patch("app.notification.logger") as mock_logger:
        await manager.send(
            level=NotificationLevel.ERROR,
            title="测试通知",
            message="测试消息",
        )

        # 验证日志记录
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "测试通知" in call_args
        assert "测试消息" in call_args
        assert "元数据" not in call_args  # 无元数据时不应包含
