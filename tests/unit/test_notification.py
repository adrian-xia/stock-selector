"""测试通知报警模块。"""

import pytest
import logging
from unittest.mock import AsyncMock, patch

import app.notification as notification_module
from app.notification import NotificationLevel, NotificationManager, TelegramChannel


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


@pytest.mark.asyncio
async def test_send_report_persists_markdown_and_sends_document(tmp_path, monkeypatch):
    """测试 send_report 会落盘并通过 Telegram 发送附件。"""
    manager = NotificationManager()
    channel = TelegramChannel("bot123:token", "chat456")
    manager._channels = [channel]

    monkeypatch.setattr(notification_module.settings, "report_output_dir", str(tmp_path))

    with (
        patch.object(manager, "send", new=AsyncMock()) as mock_send,
        patch.object(channel, "send_document", new=AsyncMock(return_value=True)) as mock_send_document,
    ):
        await manager.send_report(
            title="测试报告",
            summary_text="这里是摘要",
            markdown_content="# 报告标题\n\n内容",
            filename="demo_report.md",
        )

    report_path = tmp_path / "demo_report.md"
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == "# 报告标题\n\n内容"
    mock_send.assert_awaited_once()
    mock_send_document.assert_awaited_once()
