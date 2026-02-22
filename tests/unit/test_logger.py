"""logger 模块单元测试。

测试 JSONFormatter 和 setup_logging 的核心逻辑。
"""

import json
import logging

from unittest.mock import patch

import pytest

from app.logger import JSONFormatter, setup_logging


class TestJSONFormatter:
    """JSONFormatter 测试。"""

    def test_basic_format(self):
        """基本 JSON 格式输出。"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "hello world"
        assert data["lineno"] == 42
        assert "timestamp" in data

    def test_exception_included(self):
        """异常信息包含在 traceback 字段中。"""
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert "traceback" in data
        assert "ValueError: test error" in data["traceback"]

    def test_no_exception_no_traceback(self):
        """无异常时不包含 traceback 字段。"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="ok",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert "traceback" not in data

    def test_output_is_single_line(self):
        """输出为单行 JSON。"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="multi\nline\nmessage",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        # JSON 内部的换行会被转义，输出本身是单行
        assert "\n" not in output or output.count("\n") == 0


class TestSetupLogging:
    """setup_logging 测试。"""

    def teardown_method(self):
        """每个测试后清理 root logger handlers。"""
        root = logging.getLogger()
        root.handlers.clear()

    @patch("app.config.settings")
    def test_development_uses_text_format(self, mock_settings):
        """开发环境使用文本格式。"""
        mock_settings.app_env = "development"
        mock_settings.log_format = ""
        mock_settings.log_file_max_bytes = 1024
        mock_settings.log_file_backup_count = 1

        setup_logging("INFO")

        root = logging.getLogger()
        # 应有 3 个 handler：console + main file + error file
        assert len(root.handlers) == 3
        # console handler 使用文本格式
        console = root.handlers[0]
        assert not isinstance(console.formatter, JSONFormatter)

    @patch("app.config.settings")
    def test_production_uses_json_format(self, mock_settings):
        """生产环境使用 JSON 格式。"""
        mock_settings.app_env = "production"
        mock_settings.log_format = ""
        mock_settings.log_file_max_bytes = 1024
        mock_settings.log_file_backup_count = 1

        setup_logging("INFO")

        root = logging.getLogger()
        console = root.handlers[0]
        assert isinstance(console.formatter, JSONFormatter)

    @patch("app.config.settings")
    def test_explicit_json_format(self, mock_settings):
        """显式指定 JSON 格式。"""
        mock_settings.app_env = "development"
        mock_settings.log_format = "json"
        mock_settings.log_file_max_bytes = 1024
        mock_settings.log_file_backup_count = 1

        setup_logging("INFO")

        root = logging.getLogger()
        console = root.handlers[0]
        assert isinstance(console.formatter, JSONFormatter)

    @patch("app.config.settings")
    def test_error_handler_level(self, mock_settings):
        """错误日志 handler 级别为 WARNING。"""
        mock_settings.app_env = "development"
        mock_settings.log_format = "text"
        mock_settings.log_file_max_bytes = 1024
        mock_settings.log_file_backup_count = 1

        setup_logging("DEBUG")

        root = logging.getLogger()
        # 第 3 个 handler 是 error handler
        error_handler = root.handlers[2]
        assert error_handler.level == logging.WARNING

    @patch("app.config.settings")
    def test_third_party_suppressed(self, mock_settings):
        """第三方库日志被抑制到 WARNING。"""
        mock_settings.app_env = "development"
        mock_settings.log_format = "text"
        mock_settings.log_file_max_bytes = 1024
        mock_settings.log_file_backup_count = 1

        setup_logging("DEBUG")

        assert logging.getLogger("httpcore").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("asyncio").level == logging.WARNING
        assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING
        assert logging.getLogger("apscheduler").level == logging.WARNING
