"""
Metrics collection and exposure for FastAPI applications.

This module provides support for collecting and exposing application metrics
using Prometheus, allowing monitoring systems to track performance and usage.

Limitations:
- Only Prometheus metrics are included by default (no custom metric registration API)
- No built-in alerting or notification features
- Metrics endpoint is public unless protected by other means
"""

import time
from typing import Callable, List, Optional

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


def _get_route_path(request: Request) -> str:
    """
    Extract the route pattern from the request scope instead of the raw URL path.

    FastAPI populates request.scope["route"] after route matching, which happens
    during call_next(). Calling this function after call_next() ensures the route
    is available, so /api/v1/wsi/tiles/some-uuid/5/27/1 is recorded as
    /api/v1/wsi/tiles/{upload_id}/{z}/{x}/{y} — keeping cardinality under control.

    Falls back to raw path for unmatched routes (404s etc.).
    """
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return route.path
    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics.

    This middleware tracks request counts, latency, and exceptions
    for all HTTP requests processed by the application.

    Args:
        exclude_paths: URL prefixes to skip metric collection for.
        group_paths: If True, uses FastAPI route patterns (e.g. /items/{id})
            instead of raw URLs as the endpoint label. This keeps Prometheus
            cardinality low when path parameters contain dynamic values like UUIDs.
            Defaults to False to preserve backwards-compatible behaviour — opt in
            explicitly via METRICS_GROUP_PATHS=true in settings.
    """

    def __init__(
        self,
        app: FastAPI,
        exclude_paths: List[str] = None,
        group_paths: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(app, *args, **kwargs)
        self.exclude_paths = exclude_paths or []
        self.group_paths = group_paths

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics collection for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        method = request.method

        # Use raw path for in-progress gauge — route is not matched yet at this point.
        # This is a known limitation: in-progress uses raw path but count/latency
        # use the grouped route pattern. The gauge is informational only.
        raw_path = request.url.path
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=raw_path).inc()

        # Track request latency
        start_time = time.time()

        try:
            response = await call_next(request)

            # Route is matched now — resolve endpoint label based on group_paths setting.
            endpoint = _get_route_path(request) if self.group_paths else raw_path
            status_code = response.status_code

            # Record request count
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()

            return response

        except Exception as exc:
            endpoint = _get_route_path(request) if self.group_paths else raw_path
            EXCEPTIONS_COUNT.labels(
                method=method, endpoint=endpoint, exception_type=type(exc).__name__
            ).inc()
            raise

        finally:
            endpoint = _get_route_path(request) if self.group_paths else raw_path
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(
                time.time() - start_time
            )
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=raw_path).dec()


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

    Settings keys (all optional):
        METRICS_PATH: URL path for the metrics endpoint. Default: /metrics
        METRICS_EXCLUDE_PATHS: List of URL prefixes to skip. Default: [/metrics, /health]
        METRICS_GROUP_PATHS: Group dynamic path params into route patterns. Default: False
    """
    log = ensure_logger(logger, __name__, settings)

    # Get metrics configuration
    metrics_path = getattr(settings, "METRICS_PATH", "/metrics")
    exclude_paths = getattr(settings, "METRICS_EXCLUDE_PATHS", ["/metrics", "/health"])
    group_paths = getattr(settings, "METRICS_GROUP_PATHS", False)

    # Create router for metrics endpoint
    router = APIRouter(tags=["monitoring"])

    @router.get(metrics_path)
    async def metrics():
        """
        Expose Prometheus metrics.

        Returns all collected metrics in the Prometheus text format.
        """
        return Response(
            content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST
        )

    app.add_middleware(
        PrometheusMiddleware, exclude_paths=exclude_paths, group_paths=group_paths
    )

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
