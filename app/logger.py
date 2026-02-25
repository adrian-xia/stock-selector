"""应用日志配置模块。

支持环境感知格式切换：
- development: 可读文本格式
- production: JSON 结构化格式

支持日志文件轮转和错误日志独立文件。
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON 结构化日志格式化器。

    每条日志输出为单行 JSON 对象，便于日志分析工具解析。
    """

    # 东八区时区
    _TZ_CST = timezone(timedelta(hours=8))

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=self._TZ_CST
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }

        # 包含异常堆栈
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["traceback"] = "".join(
                traceback.format_exception(*record.exc_info)
            )

        # 包含 extra 字段（排除标准 LogRecord 属性）
        standard_attrs = {
            "name", "msg", "args", "created", "relativeCreated",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "filename", "module", "pathname", "thread", "threadName",
            "process", "processName", "levelname", "levelno", "message",
            "msecs", "taskName",
        }
        extra = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_")
        }
        if extra:
            log_entry["extra"] = extra

        return json.dumps(log_entry, ensure_ascii=False, default=str)

def setup_logging(level: str = "INFO") -> None:
    """配置应用日志，支持环境感知格式切换和日志轮转。

    - development 环境：可读文本格式
    - production 环境：JSON 结构化格式
    - 主日志文件：logs/app.log（轮转）
    - 错误日志文件：logs/app-error.log（仅 WARNING+，轮转）
    """
    from app.config import settings

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # 确定日志格式
    log_format = settings.log_format
    if not log_format:
        log_format = "json" if settings.app_env == "production" else "text"

    # 创建格式化器
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        # text 格式使用东八区时间
        class CSTFormatter(logging.Formatter):
            _TZ_CST = timezone(timedelta(hours=8))

            def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
                dt = datetime.fromtimestamp(record.created, tz=self._TZ_CST)
                if datefmt:
                    return dt.strftime(datefmt)
                return dt.isoformat(timespec="seconds")

        formatter = CSTFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有 handlers（避免重复添加）
    root_logger.handlers.clear()

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 主日志文件（轮转）
    main_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=settings.log_file_max_bytes,
        backupCount=settings.log_file_backup_count,
        encoding="utf-8",
    )
    main_handler.setFormatter(formatter)
    root_logger.addHandler(main_handler)

    # 错误日志文件（仅 WARNING+，轮转）
    error_handler = RotatingFileHandler(
        log_dir / "app-error.log",
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=10,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # 抑制第三方库噪音日志
    for lib in ("httpcore", "httpx", "asyncio", "sqlalchemy.engine", "apscheduler"):
        logging.getLogger(lib).setLevel(logging.WARNING)
