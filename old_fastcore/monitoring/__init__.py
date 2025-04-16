"""
Monitoring tools for FastAPI applications.

This module provides tools for monitoring and gaining operational visibility
into FastAPI applications, including metrics collection, health checks,
and instrumentation.
"""

from fastcore.monitoring.health import (
    HealthCheck,
    HealthCheckResult,
    HealthStatus,
    ServiceHealthCheck,
    register_health_check,
)
from fastcore.monitoring.instrumentation import (
    RequestMetrics,
    endpoint_metrics,
    instrument_app,
)
from fastcore.monitoring.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricCollector,
    configure_metrics,
    get_metrics,
)

__all__ = [
    # Health checks
    "HealthCheck",
    "HealthCheckResult",
    "HealthStatus",
    "ServiceHealthCheck",
    "register_health_check",
    # Metrics collection
    "Counter",
    "Gauge",
    "Histogram",
    "MetricCollector",
    "configure_metrics",
    "get_metrics",
    # Instrumentation
    "instrument_app",
    "RequestMetrics",
    "endpoint_metrics",
]
