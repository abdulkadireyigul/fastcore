"""
Instrumentation utilities for FastAPI applications.

This module provides tools for automatically instrumenting FastAPI applications
to collect metrics and telemetry data.
"""

import functools
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from fastapi import FastAPI, Request, Response
from fastcore.monitoring.metrics import Histogram, MetricCollector, get_metrics
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match
from starlette.types import ASGIApp

from fastcore.logging import get_logger
from fastcore.middleware.timing import TimingMiddleware

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RequestMetrics(BaseHTTPMiddleware):
    """Middleware for collecting request metrics."""

    def __init__(
        self,
        app: ASGIApp,
        metrics_collector: Optional[MetricCollector] = None,
        exclude_paths: Optional[List[str]] = None,
    ):
        """
        Initialize the request metrics middleware.

        Args:
            app: The ASGI application
            metrics_collector: Metrics collector to use (or global if None)
            exclude_paths: List of paths to exclude from metrics
        """
        super().__init__(app)
        self.metrics_collector = metrics_collector or get_metrics()
        self.exclude_paths = exclude_paths or ["/metrics", "/health"]

        # Create metrics
        self.request_count = self.metrics_collector.counter(
            "http_requests_total",
            "Total number of HTTP requests",
            ["method", "path", "status_code"],
        )

        self.request_duration = self.metrics_collector.histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            ["method", "path", "status_code"],
        )

        self.requests_in_progress = self.metrics_collector.gauge(
            "http_requests_in_progress",
            "Number of HTTP requests currently in progress",
            ["method"],
        )

        logger.info("Request metrics middleware initialized")

    def should_process(self, request: Request) -> bool:
        """Check if this request should be processed."""
        path = request.url.path
        return not any(
            path.startswith(exclude_path) for exclude_path in self.exclude_paths
        )

    async def dispatch(self, request: Request, call_next):
        """Process the request and collect metrics."""
        # Skip metrics collection for excluded paths
        if not self.should_process(request):
            return await call_next(request)

        # Determine the route path for more accurate metrics
        route_path = request.url.path
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                route_path = route.path
                break

        method = request.method

        # Increment in-progress counter
        self.requests_in_progress.inc(1, {"method": method})

        # Track request time
        start_time = time.time()

        try:
            # Process the request
            response = await call_next(request)

            # Record request duration
            duration = time.time() - start_time
            status_code = response.status_code

            # Record metrics
            self.request_count.inc(
                1,
                {"method": method, "path": route_path, "status_code": str(status_code)},
            )
            self.request_duration.observe(
                duration,
                {"method": method, "path": route_path, "status_code": str(status_code)},
            )

            return response

        except Exception as e:
            # Record metrics for exceptions
            duration = time.time() - start_time

            self.request_count.inc(
                1, {"method": method, "path": route_path, "status_code": "500"}
            )
            self.request_duration.observe(
                duration, {"method": method, "path": route_path, "status_code": "500"}
            )

            # Re-raise the exception
            raise

        finally:
            # Always decrement in-progress counter
            self.requests_in_progress.dec(1, {"method": method})


def endpoint_metrics(
    path_name: Optional[str] = None, metrics_collector: Optional[MetricCollector] = None
) -> Callable[[F], F]:
    """
    Decorator for measuring individual endpoint metrics.

    Args:
        path_name: Optional custom name for the endpoint
        metrics_collector: Optional metrics collector to use

    Returns:
        Decorated function

    Example:
        ```python
        @app.get("/items/{item_id}")
        @endpoint_metrics(path_name="get_item")
        async def read_item(item_id: str):
            # This endpoint will be measured
            return {"item_id": item_id}
        ```
    """

    def decorator(func: F) -> F:
        collector = metrics_collector or get_metrics()

        # Use function name if path name not provided
        name = path_name or func.__name__

        # Create metrics for this endpoint
        histogram = collector.histogram(
            f"endpoint_{name}_duration_seconds",
            f"Duration of {name} endpoint in seconds",
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                histogram.observe(duration)

        return cast(F, wrapper)

    return decorator


def instrument_app(
    app: FastAPI,
    exclude_paths: Optional[List[str]] = None,
    metrics_path: str = "/metrics",
    health_path: str = "/health",
    add_timing_middleware: bool = True,
) -> FastAPI:
    """
    Instrument a FastAPI application with monitoring capabilities.

    This function adds request metrics middleware, metrics endpoint,
    and optionally timing middleware to a FastAPI application.

    Args:
        app: FastAPI application to instrument
        exclude_paths: Paths to exclude from metrics collection
        metrics_path: Path for the metrics endpoint
        health_path: Path for the health check endpoint
        add_timing_middleware: Whether to add the timing middleware

    Returns:
        The instrumented FastAPI application

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.monitoring import instrument_app

        app = FastAPI()
        instrument_app(app)
        ```
    """
    # Initialize standard exclude paths
    standard_exclude = ["/metrics", "/health", "/openapi.json", "/docs", "/redoc"]
    if exclude_paths:
        exclude_paths.extend(standard_exclude)
    else:
        exclude_paths = standard_exclude

    # Configure metrics endpoint
    from fastcore.monitoring.metrics import configure_metrics

    configure_metrics(app, path=metrics_path)

    # Add request metrics middleware
    app.add_middleware(RequestMetrics, exclude_paths=exclude_paths)

    # Add timing middleware if requested
    if add_timing_middleware:
        from fastcore.middleware.timing import configure_timing

        configure_timing(
            app,
            header_name="X-Process-Time",
            log_timing=True,
            exclude_paths=exclude_paths,
        )

    # Register health check endpoint
    from fastcore.monitoring.health import register_health_check

    register_health_check(app, path=health_path)

    logger.info(f"Application instrumented with monitoring features")
    return app
