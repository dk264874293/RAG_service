"""
请求限流中间件
使用SlowAPI库实现基于IP的速率限制
"""

from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import config


def get_real_client_ip(request: Request) -> str:
    """
    获取客户端真实IP地址

    考虑代理和负载均衡器，优先从X-Forwarded-For获取真实IP

    Args:
        request: FastAPI请求对象

    Returns:
        str: 客户端IP地址
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return get_remote_address(request)


limiter = Limiter(
    key_func=get_real_client_ip,
    default_limits=["200/hour"],  # 默认限制：每小时200次请求
    storage_uri="memory://",  # 使用内存存储（生产环境建议使用Redis）
    headers_enabled=True,  # 在响应头中包含限流信息
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    限流超出异常处理器

    Args:
        request: FastAPI请求对象
        exc: 限流异常

    Returns:
        JSON响应，包含限流信息
    """
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "请求过于频繁",
            "message": str(exc.detail),
            "retry_after": exc.retry_after,
        },
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(exc.rate_limit.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(exc.reset_time),
        },
    )
