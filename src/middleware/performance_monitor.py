"""
性能监控中间件
跟踪请求耗时、API调用统计和性能指标
"""

import time
from typing import Dict, Any, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Prometheus指标
request_count = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)

request_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
)

dashscope_api_calls = Counter(
    "dashscope_api_calls_total", "Total Dashscope API calls", ["operation"]
)

dashscope_api_duration = Histogram(
    "dashscope_api_duration_seconds", "Dashscope API call duration", ["operation"]
)

# 内存中的性能统计
performance_stats: Dict[str, Dict[str, Any]] = {
    "requests": {},
    "endpoints": {},
}


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """
    性能监控中间件

    跟踪所有HTTP请求的性能指标，包括：
    - 请求耗时
    - 状态码分布
    - 端点调用统计
    - 并发请求数
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并记录性能指标

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP响应对象
        """
        method = request.method
        path = request.url.path

        if path == "/metrics":
            return await call_next(request)

        request_in_progress.labels(method=method, endpoint=path).inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status = response.status_code

            duration = time.time() - start_time
            request_duration.labels(method=method, endpoint=path).observe(duration)
            request_count.labels(method=method, endpoint=path, status=status).inc()

            self._update_stats(method, path, status, duration)

            if duration > 1.0:
                logger.warning(
                    "slow_request",
                    method=method,
                    path=path,
                    duration=duration,
                    status=status,
                )

            return response

        finally:
            request_in_progress.labels(method=method, endpoint=path).dec()

    def _update_stats(self, method: str, path: str, status: int, duration: float):
        """
        更新内存中的性能统计

        Args:
            method: HTTP方法
            path: 请求路径
            status: HTTP状态码
            duration: 请求耗时（秒）
        """
        key = f"{method}:{path}"

        if key not in performance_stats["requests"]:
            performance_stats["requests"][key] = {
                "count": 0,
                "total_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "status_codes": {},
            }

        stats = performance_stats["requests"][key]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["max_duration"] = max(stats["max_duration"], duration)

        if status not in stats["status_codes"]:
            stats["status_codes"][status] = 0
        stats["status_codes"][status] += 1

    def get_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息

        Returns:
            Dict[str, Any]: 性能统计数据
        """
        result = {}

        for key, stats in performance_stats["requests"].items():
            if stats["count"] > 0:
                result[key] = {
                    "count": stats["count"],
                    "avg_duration": stats["total_duration"] / stats["count"],
                    "min_duration": stats["min_duration"],
                    "max_duration": stats["max_duration"],
                    "status_codes": stats["status_codes"],
                }

        return result


class DashscopeAPIMonitor:
    """
    Dashscope API调用监控

    跟踪Dashscope API的调用次数和耗时
    """

    @staticmethod
    def track_call(operation: str, duration: float):
        """
        跟踪API调用

        Args:
            operation: 操作类型（如：embedding）
            duration: 调用耗时（秒）
        """
        dashscope_api_calls.labels(operation=operation).inc()
        dashscope_api_duration.labels(operation=operation).observe(duration)

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """
        获取API调用统计

        Returns:
            Dict[str, Any]: API调用统计数据
        """
        return {
            "total_calls": dashscope_api_calls._value.get()
            if hasattr(dashscope_api_calls, "_value")
            else 0,
        }


def get_prometheus_metrics() -> bytes:
    """
    获取Prometheus格式的指标

    Returns:
        bytes: Prometheus文本格式的指标
    """
    return generate_latest()
