"""
Monitoring manager for FastAPI applications.

This module provides the main entry point for configuring monitoring 
in a FastAPI application, including health checks and metrics.
"""

from typing import Optional

from fastapi import FastAPI

from fastcore.config.base import BaseAppSettings
from fastcore.logging import Logger, ensure_logger
from fastcore.monitoring.health import setup_health_endpoint
from fastcore.monitoring.metrics import setup_metrics_endpoint


def setup_monitoring(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Configure monitoring for a FastAPI application.

    This function sets up health checks, metrics collection, and instrumentation
    for monitoring a FastAPI application in production environments.

    Features:
    - Health check endpoint (configurable)
    - Prometheus metrics endpoint (configurable)

    Limitations:
    - Only Prometheus metrics and basic health checks are included by default
    - No full distributed tracing (e.g., OpenTelemetry, Jaeger, Zipkin)
    - No custom metric registration API (only built-in HTTP metrics)
    - No built-in alerting or notification features
    - Metrics endpoint is public unless protected by other means

    Args:
        app: FastAPI application instance
        settings: Application settings
        logger: Optional logger for monitoring events
    """
    log = ensure_logger(logger, __name__, settings)

    # Determine if monitoring is enabled
    # enabled = getattr(settings, "MONITORING_ENABLED", True)
    # if not enabled:
    #     log.info("Monitoring is disabled via settings")
    #     return

    # Get monitoring settings with safe defaults
    # metrics_enabled = getattr(settings, "METRICS_ENABLED", True)
    # health_enabled = getattr(settings, "HEALTH_ENABLED", True)

    # Setup each monitoring component as configured
    # if health_enabled:
    setup_health_endpoint(app, settings, log)

    # if metrics_enabled:
    setup_metrics_endpoint(app, settings, log)

    log.info("Monitoring configured successfully")
