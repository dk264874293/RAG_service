"""
重试和超时控制
提供自动重试、超时控制和退避策略
"""

import asyncio
import logging
import time
from typing import Callable, TypeVar, Type, Tuple, Optional, Any, List, Union
from functools import wraps
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BackoffStrategy(Enum):
    """退避策略"""
    FIXED = "fixed"           # 固定延迟
    LINEAR = "linear"         # 线性增长
    EXPONENTIAL = "exponential"  # 指数增长
    FIBONACCI = "fibonacci"   # 斐波那契数列


class RetryCondition:
    """重试条件判断"""

    @staticmethod
    def on_exception(exception_types: Union[Type[Exception], Tuple[Type[Exception], ...]]) -> Callable[[Exception], bool]:
        """基于异常类型的重试条件"""
        def should_retry(exc: Exception) -> bool:
            return isinstance(exc, exception_types)
        return should_retry

    @staticmethod
    def on_result(predicate: Callable[[Any], bool]) -> Callable[[Any], bool]:
        """基于结果的重试条件"""
        def should_retry(result: Any) -> bool:
            return predicate(result)
        return should_retry

    @staticmethod
    def on_any_exception() -> Callable[[Exception], bool]:
        """任何异常都重试"""
        def should_retry(exc: Exception) -> bool:
            return True
        return should_retry


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        max_delay: float = 60.0,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_jitter: float = 1.0,
        retry_on_exception: Optional[Callable[[Exception], bool]] = None,
        retry_on_result: Optional[Callable[[Any], bool]] = None,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
    ):
        self.max_attempts = max_attempts
        self.max_delay = max_delay
        self.backoff_strategy = backoff_strategy
        self.base_delay = base_delay
        self.max_jitter = max_jitter
        self.retry_on_exception = retry_on_exception or RetryCondition.on_any_exception()
        self.retry_on_result = retry_on_result
        self.on_retry = on_retry


class RetryExecutor:
    """重试执行器"""

    def __init__(self, config: RetryConfig):
        self.config = config
        self._attempt_counts: dict = {}

    def _calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        delay = self.config.base_delay

        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.config.base_delay

        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay * attempt

        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** (attempt - 1))

        elif self.config.backoff_strategy == BackoffStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(attempt)

        # 应用最大延迟限制
        delay = min(delay, self.config.max_delay)

        # 添加抖动（避免雷群效应）
        import random
        jitter = random.uniform(0, min(self.config.max_jitter, delay * 0.1))

        return delay - jitter

    def _fibonacci(self, n: int) -> int:
        """计算斐波那契数列"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b

    def execute_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """同步执行带重试"""
        last_exception = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)

                # 检查结果是否需要重试
                if self.config.retry_on_result and attempt < self.config.max_attempts:
                    if self.config.retry_on_result(result):
                        self._handle_retry(attempt, None)
                        continue

                return result

            except Exception as e:
                last_exception = e

                # 检查异常是否需要重试
                should_retry = (
                    attempt < self.config.max_attempts
                    and self.config.retry_on_exception(e)
                )

                if should_retry:
                    delay = self._calculate_delay(attempt)
                    self._handle_retry(attempt, delay, e)
                    time.sleep(delay)
                    continue

                # 不重试，直接抛出
                raise

        # 所有尝试都失败
        raise last_exception if last_exception else Exception("All retry attempts failed")

    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """异步执行带重试"""
        last_exception = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)

                # 检查结果是否需要重试
                if self.config.retry_on_result and attempt < self.config.max_attempts:
                    if self.config.retry_on_result(result):
                        self._handle_retry(attempt, None)
                        continue

                return result

            except Exception as e:
                last_exception = e

                # 检查异常是否需要重试
                should_retry = (
                    attempt < self.config.max_attempts
                    and self.config.retry_on_exception(e)
                )

                if should_retry:
                    delay = self._calculate_delay(attempt)
                    self._handle_retry(attempt, delay, e)
                    await asyncio.sleep(delay)
                    continue

                # 不重试，直接抛出
                raise

        # 所有尝试都失败
        raise last_exception if last_exception else Exception("All retry attempts failed")

    def _handle_retry(
        self,
        attempt: int,
        delay: Optional[float],
        exception: Optional[Exception] = None,
    ) -> None:
        """处理重试逻辑"""
        if self.config.on_retry:
            self.config.on_retry(attempt, exception)

        logger.warning(
            f"Retry attempt {attempt}/{self.config.max_attempts}"
            + (f" after {delay:.2f}s delay" if delay else "")
            + (f": {exception}" if exception else "")
        )


def retry(
    max_attempts: int = 3,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    exception_types: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
):
    """
    重试装饰器（同步函数）

    用法:
        @retry(max_attempts=3, exception_types=(ConnectionError, TimeoutError))
        def fetch_data(url):
            return requests.get(url)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        config = RetryConfig(
            max_attempts=max_attempts,
            max_delay=max_delay,
            backoff_strategy=backoff_strategy,
            base_delay=base_delay,
            retry_on_exception=RetryCondition.on_exception(exception_types),
        )
        executor = RetryExecutor(config)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return executor.execute_sync(func, *args, **kwargs)

        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    exception_types: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
):
    """
    重试装饰器（异步函数）

    用法:
        @async_retry(max_attempts=3, exception_types=(ConnectionError, TimeoutError))
        async def fetch_data_async(url):
            return await aiohttp.get(url)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        config = RetryConfig(
            max_attempts=max_attempts,
            max_delay=max_delay,
            backoff_strategy=backoff_strategy,
            base_delay=base_delay,
            retry_on_exception=RetryCondition.on_exception(exception_types),
        )
        executor = RetryExecutor(config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await executor.execute_async(func, *args, **kwargs)

        return wrapper
    return decorator


def timeout(seconds: float, exception_type: Type[Exception] = TimeoutError):
    """
    超时装饰器（同步函数）

    用法:
        @timeout(seconds=5.0)
        def slow_operation():
            time.sleep(10)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal

            def timeout_handler(signum, frame):
                raise exception_type(f"Function {func.__name__} timed out after {seconds}s")

            # 设置信号处理器
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds))

            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

            return result

        return wrapper
    return decorator


def async_timeout(seconds: float, exception_type: Type[Exception] = asyncio.TimeoutError):
    """
    超时装饰器（异步函数）

    用法:
        @async_timeout(seconds=5.0)
        async def slow_operation():
            await asyncio.sleep(10)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise exception_type(f"Function {func.__name__} timed out after {seconds}s")

        return wrapper
    return decorator


# ============================================
# 服务降级
# ============================================

class FallbackResult:
    """降级结果"""
    def __init__(self, value: Any, is_fallback: bool = True, reason: str = ""):
        self.value = value
        self.is_fallback = is_fallback
        self.reason = reason


def fallback(
    fallback_func: Callable,
    on_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
):
    """
    降级装饰器

    当主函数失败时，使用降级函数

    用法:
        def fallback_search(query):
            return []  # 返回空结果

        @fallback(fallback_search, on_exceptions=(CircuitBreakerError, TimeoutError))
        async def search(query):
            return await vector_search(query)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return FallbackResult(result, is_fallback=False)
            except on_exceptions as e:
                logger.warning(f"Primary function failed, using fallback: {e}")
                fallback_result = fallback_func(*args, **kwargs)
                return FallbackResult(
                    fallback_result,
                    is_fallback=True,
                    reason=str(e)
                )

        return wrapper
    return decorator


def async_fallback(
    fallback_func: Callable,
    on_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
):
    """异步降级装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return FallbackResult(result, is_fallback=False)
            except on_exceptions as e:
                logger.warning(f"Primary function failed, using fallback: {e}")
                fallback_result = await fallback_func(*args, **kwargs)
                return FallbackResult(
                    fallback_result,
                    is_fallback=True,
                    reason=str(e)
                )

        return wrapper
    return decorator
