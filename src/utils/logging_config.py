"""
结构化日志配置
使用structlog提供JSON格式的结构化日志
"""

import logging
import sys
from typing import Any, Dict
import structlog
from structlog.types import Processor
import config


def add_app_context(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    添加应用程序上下文到日志记录

    Args:
        logger: 日志记录器
        method_name: 方法名
        event_dict: 事件字典

    Returns:
        Dict[str, Any]: 更新后的事件字典
    """
    event_dict["app"] = "rag_service"
    event_dict["environment"] = (
        "development" if config.settings.debug_mode else "production"
    )
    return event_dict


def configure_logging() -> None:
    """
    配置结构化日志系统

    设置structlog和标准logging模块，支持JSON格式输出
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_app_context,
    ]

    if config.settings.debug_mode:
        shared_processors.append(structlog.dev.ConsoleRenderer())
    else:
        shared_processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    logging.getLogger().handlers[0].setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer()
            if config.settings.debug_mode
            else structlog.processors.JSONRenderer(),
        )
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    获取命名日志记录器

    Args:
        name: 日志记录器名称（通常使用__name__）

    Returns:
        structlog.stdlib.BoundLogger: 配置好的日志记录器
    """
    return structlog.get_logger(name)
