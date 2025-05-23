"""
Monitoring module for FastAPI applications.

This module provides health checks, metrics collection, and instrumentation
capabilities for monitoring FastAPI applications in production environments.

Limitations:
- Only Prometheus metrics and basic health checks are included by default
- No full distributed tracing (e.g., OpenTelemetry, Jaeger, Zipkin)
- No custom metric registration API (only built-in HTTP metrics)
- No built-in alerting or notification features
- Metrics endpoint is public unless protected by other means
"""

from fastcore.monitoring.health import setup_health_endpoint
from fastcore.monitoring.manager import setup_monitoring
from fastcore.monitoring.metrics import setup_metrics_endpoint

__all__ = [
    "setup_monitoring",
    "setup_health_endpoint",
    "setup_metrics_endpoint",
]
