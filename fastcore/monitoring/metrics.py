"""
Metrics collection and exposure for FastAPI applications.

This module provides support for collecting and exposing application metrics
using Prometheus, allowing monitoring systems to track performance and usage.
"""

import time
from typing import Callable, Dict, List, Optional

from fastapi import APIRouter, FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware

from fastcore.config.base import BaseAppSettings
from fastcore.logging import Logger, ensure_logger

# Default metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)

REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "endpoint"],
)

EXCEPTIONS_COUNT = Counter(
    "http_exceptions_total",
    "Total count of exceptions raised during HTTP requests",
    ["method", "endpoint", "exception_type"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics.

    This middleware tracks request counts, latency, and exceptions
    for all HTTP requests processed by the application.
    """

    def __init__(self, app: FastAPI, exclude_paths: List[str] = None, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.exclude_paths = exclude_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics collection for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        method = request.method
        path = request.url.path

        # Track in-progress requests
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).inc()

        # Track request latency
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Record request count
            REQUEST_COUNT.labels(
                method=method, endpoint=path, status_code=status_code
            ).inc()

            return response
        except Exception as exc:
            # Record exception
            EXCEPTIONS_COUNT.labels(
                method=method, endpoint=path, exception_type=type(exc).__name__
            ).inc()
            raise
        finally:
            # Record request latency
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(
                time.time() - start_time
            )

            # Decrement in-progress counter
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).dec()


def setup_metrics_endpoint(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Set up metrics collection and exposure endpoint.

    Args:
        app: FastAPI application
        settings: Application settings
        logger: Optional logger
    """
    log = ensure_logger(logger, __name__, settings)

    # Get metrics configuration
    metrics_path = getattr(settings, "METRICS_PATH", "/metrics")
    exclude_paths = getattr(settings, "METRICS_EXCLUDE_PATHS", ["/metrics", "/health"])

    # Create router for metrics endpoint
    router = APIRouter(tags=["monitoring"])

    @router.get(metrics_path)
    async def metrics():
        """
        Expose Prometheus metrics.

        This endpoint returns all collected metrics in the Prometheus text format.
        """
        return Response(
            content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST
        )

    # Add Prometheus middleware for metrics collection
    app.add_middleware(PrometheusMiddleware, exclude_paths=exclude_paths)

    # Add metrics endpoint
    app.include_router(router)
    log.info(f"Metrics endpoint configured at {metrics_path}")

    # Register app info metric
    app_info = Gauge(
        "fastapi_app_info", "FastAPI application information", ["app_name", "version"]
    )
    app_info.labels(
        app_name=getattr(app, "title", "fastapi"),
        version=getattr(app, "version", "unknown"),
    ).set(1)

    log.info("Prometheus metrics collection configured")
