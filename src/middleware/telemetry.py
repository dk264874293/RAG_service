"""
OpenTelemetry链路追踪配置
提供分布式追踪、指标和日志关联
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

logger = logging.getLogger(__name__)


class OpenTelemetryConfig:
    """OpenTelemetry配置管理"""

    def __init__(
        self,
        service_name: str = "rag-service",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        enable_prometheus: bool = True,
        sample_rate: float = 0.1,  # 10%采样率
    ):
        self.service_name = service_name
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.enable_prometheus = enable_prometheus
        self.sample_rate = sample_rate

        self._tracer_provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None

    def setup_telemetry(self) -> None:
        """初始化完整的可观测性栈"""
        logger.info("Initializing OpenTelemetry...")

        # 创建资源（服务标识）
        resource = Resource(attributes={
            SERVICE_NAME: self.service_name,
            "service.version": "1.0.0",
            "deployment.environment": "production",
        })

        # 设置追踪
        self._setup_tracing(resource)

        # 设置指标
        self._setup_metrics(resource)

        logger.info("OpenTelemetry initialized successfully")

    def _setup_tracing(self, resource: Resource) -> None:
        """设置分布式追踪"""
        # 配置Jaeger导出器
        jaeger_exporter = JaegerExporter(
            agent_host_name=self.jaeger_host,
            agent_port=self.jaeger_port,
            max_tag_value_length=4096,
        )

        # 创建TracerProvider
        self._tracer_provider = TracerProvider(
            resource=resource,
            sampler=trace.samplers.TraceIdRatioBased(self.sample_rate),
        )

        # 添加批量Span处理器
        self._tracer_provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter, max_queue_size=2048)
        )

        # 设置全局TracerProvider
        trace.set_tracer_provider(self._tracer_provider)

        logger.info(f"Tracing configured: Jaeger at {self.jaeger_host}:{self.jaeger_port}")

    def _setup_metrics(self, resource: Resource) -> None:
        """设置指标收集"""
        if self.enable_prometheus:
            # Prometheus指标导出器
            prometheus_reader = PrometheusMetricReader(
                preferred_temporal_unit="ms"
            )

            self._meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[prometheus_reader],
            )

            metrics.set_meter_provider(self._meter_provider)

            logger.info("Metrics configured: Prometheus exporter")

    def instrument_fastapi(self, app) -> None:
        """自动检测FastAPI应用"""
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=self._tracer_provider,
            meter_provider=self._meter_provider,
        )
        logger.info("FastAPI instrumented")

    def instrument_httpx(self) -> None:
        """自动检测HTTPX客户端"""
        HTTPXClientInstrumentor().instrument(
            tracer_provider=self._tracer_provider,
            meter_provider=self._meter_provider,
        )
        logger.info("HTTPX instrumented")

    def instrument_sqlalchemy(self, engine) -> None:
        """自动检测SQLAlchemy"""
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            tracer_provider=self._tracer_provider,
            meter_provider=self._meter_provider,
        )
        logger.info("SQLAlchemy instrumented")

    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[None, None, None]:
        """
        手动追踪操作上下文管理器

        用法:
            with telemetry.trace_operation("custom_operation", {"key": "value"}):
                # 你的代码
        """
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span(
            operation_name,
            attributes=attributes or {},
        ) as span:
            try:
                yield
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def get_tracer(self, name: str):
        """获取命名的Tracer"""
        return trace.get_tracer(name)

    def get_meter(self, name: str):
        """获取命名的Meter"""
        return metrics.get_meter(name)


# 全局单例实例
_telemetry_config: Optional[OpenTelemetryConfig] = None


def init_telemetry(
    service_name: str = "rag-service",
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    enable_prometheus: bool = True,
    sample_rate: float = 0.1,
) -> OpenTelemetryConfig:
    """
    初始化全局OpenTelemetry配置

    应在应用启动时调用一次
    """
    global _telemetry_config

    if _telemetry_config is None:
        _telemetry_config = OpenTelemetryConfig(
            service_name=service_name,
            jaeger_host=jaeger_host,
            jaeger_port=jaeger_port,
            enable_prometheus=enable_prometheus,
            sample_rate=sample_rate,
        )
        _telemetry_config.setup_telemetry()

    return _telemetry_config


def get_telemetry_config() -> Optional[OpenTelemetryConfig]:
    """获取全局OpenTelemetry配置"""
    return _telemetry_config
