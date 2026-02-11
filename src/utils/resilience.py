"""
熔断器模式实现
防止级联失败，提供服务降级能力
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional, Dict, TypeVar
from functools import wraps
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态，请求正常通过
    OPEN = "open"          # 熔断状态，请求直接失败
    HALF_OPEN = "half_open"  # 半开状态，尝试恢复


class CircuitBreakerError(Exception):
    """熔断器异常"""
    def __init__(self, message: str, state: CircuitState, last_failure: Optional[datetime] = None):
        super().__init__(message)
        self.state = state
        self.last_failure = last_failure


class CircuitBreaker:
    """
    熔断器实现

    状态转换:
    CLOSED -> OPEN: 失败率超过阈值
    OPEN -> HALF_OPEN: 经过冷却时间后
    HALF_OPEN -> CLOSED: 探测请求成功
    HALF_OPEN -> OPEN: 探测请求失败
    """

    def __init__(
        self,
        failure_threshold: int = 5,          # 失败次数阈值
        recovery_timeout: float = 60.0,      # 熔断恢复时间（秒）
        expected_exception: Exception = Exception,
        half_open_max_calls: int = 3,         # 半开状态最大探测次数
        success_threshold: int = 2,           # 半开状态成功次数阈值
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_state_change: datetime = datetime.now()
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            # 检查是否需要从OPEN转到HALF_OPEN
            if self._state == CircuitState.OPEN:
                if (datetime.now() - self._last_state_change).total_seconds() >= self.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    logger.info(f"Circuit breaker transitioned to HALF_OPEN")

            return self._state

    def _transition_to(self, new_state: CircuitState) -> None:
        """状态转换"""
        old_state = self._state
        self._state = new_state
        self._last_state_change = datetime.now()

        logger.info(
            f"Circuit breaker state transition: {old_state.value} -> {new_state.value}, "
            f"failures={self._failure_count}, successes={self._success_count}"
        )

        # 重置计数器
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        通过熔断器调用函数

        Raises:
            CircuitBreakerError: 熔断器处于OPEN状态
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker is OPEN for {func.__name__}. "
                f"Last failure: {self._last_failure_time}",
                current_state,
                self._last_failure_time
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        """处理成功调用"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(f"Half-open success count: {self._success_count}/{self.success_threshold}")

                # 成功次数达到阈值，恢复到CLOSED
                if self._success_count >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _on_failure(self) -> None:
        """处理失败调用"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.CLOSED:
                # 达到失败阈值，熔断
                if self._failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                # 半开状态失败，重新熔断
                self._transition_to(CircuitState.OPEN)

    def get_stats(self) -> Dict[str, Any]:
        """获取熔断器统计信息"""
        with self._lock:
            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
                "last_state_change": self._last_state_change.isoformat(),
                "recovery_timeout": self.recovery_timeout,
                "failure_threshold": self.failure_threshold,
            }


class CircuitBreakerDecorator:
    """熔断器装饰器"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Exception = Exception,
        fallback: Optional[Callable] = None,
    ):
        self.name = name
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )
        self._fallback = fallback

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return self._circuit_breaker.call(func, *args, **kwargs)
            except CircuitBreakerError as e:
                if self._fallback:
                    logger.warning(
                        f"Circuit breaker OPEN for {self.name}, using fallback"
                    )
                    return self._fallback(*args, **kwargs)
                raise
        return wrapper

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._circuit_breaker.get_stats()
        stats["name"] = self.name
        stats["has_fallback"] = self._fallback is not None
        return stats


# 全局熔断器注册表
_circuit_breakers: Dict[str, CircuitBreakerDecorator] = {}


def register_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Exception = Exception,
    fallback: Optional[Callable] = None,
) -> CircuitBreakerDecorator:
    """
    注册或获取熔断器装饰器

    用法:
        # 注册
        @register_circuit_breaker("llm-service", failure_threshold=3)
        async def call_llm(prompt):
            ...

        # 获取统计
        stats = get_circuit_breaker_stats("llm-service")
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreakerDecorator(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            fallback=fallback,
        )
        logger.info(f"Registered circuit breaker: {name}")

    return _circuit_breakers[name]


def get_circuit_breaker_stats(name: str) -> Optional[Dict[str, Any]]:
    """获取熔断器统计信息"""
    if name in _circuit_breakers:
        return _circuit_breakers[name].get_stats()
    return None


def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有熔断器统计信息"""
    return {
        name: cb.get_stats()
        for name, cb in _circuit_breakers.items()
    }
