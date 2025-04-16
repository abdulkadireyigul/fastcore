"""
Request timing middleware for FastAPI applications.

This module provides middleware for tracking request durations and
performance metrics in FastAPI applications.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from fastcore.logging import get_logger

logger = get_logger(__name__)


class TimingConfig(BaseModel):
    """Configuration for timing middleware."""

    header_name: str = Field(
        default="X-Process-Time",
        description="Name of the header to use for response time information",
    )
    exclude_paths: List[str] = Field(
        default=[], description="List of paths to exclude from timing measurements"
    )
    log_timing: bool = Field(
        default=True, description="Whether to log timing information"
    )
    log_level: str = Field(
        default="debug", description="Log level for timing information"
    )
    log_threshold_ms: Optional[float] = Field(
        default=None,
        description="Only log requests that take longer than this time (in ms)",
    )


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking request processing time.

    This middleware measures the time taken to process each request
    and can add the timing information to response headers and logs.
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Process-Time",
        exclude_paths: List[str] = None,
        log_timing: bool = True,
        log_level: str = "debug",
        log_threshold_ms: Optional[float] = None,
        metrics_handler: Optional[
            Callable[[str, float, Request, Response], None]
        ] = None,
    ):
        """
        Initialize the timing middleware.

        Args:
            app: The ASGI application
            header_name: Name of the header for timing information
            exclude_paths: List of paths to exclude from timing
            log_timing: Whether to log timing information
            log_level: Log level for timing logs
            log_threshold_ms: Only log requests taking longer than this time (in ms)
            metrics_handler: Optional callback function for custom metrics processing
        """
        super().__init__(app)
        self.header_name = header_name
        self.exclude_paths = exclude_paths or []
        self.log_timing = log_timing
        self.log_level = log_level.lower()
        self.log_threshold_ms = log_threshold_ms
        self.metrics_handler = metrics_handler

        logger.info(f"Timing middleware initialized with header: {header_name}")

    def should_process(self, request: Request) -> bool:
        """
        Determine if timing should be processed for this request.

        Args:
            request: The FastAPI request

        Returns:
            True if timing should be processed, False otherwise
        """
        path = request.url.path

        # Check if path is excluded
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False

        return True

    def log_request_time(
        self, path: str, method: str, time_ms: float, status_code: int
    ) -> None:
        """
        Log the request timing information.

        Args:
            path: The request path
            method: The HTTP method
            time_ms: The processing time in milliseconds
            status_code: The HTTP status code
        """
        if not self.log_timing:
            return

        # Skip if below threshold
        if self.log_threshold_ms and time_ms < self.log_threshold_ms:
            return

        message = (
            f"Request {method} {path} took {time_ms:.2f}ms (status: {status_code})"
        )

        # Log at the appropriate level
        if self.log_level == "debug":
            logger.debug(message)
        elif self.log_level == "info":
            logger.info(message)
        elif self.log_level == "warning":
            logger.warning(message)
        else:
            # Default to debug level
            logger.debug(message)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request with timing measurement.

        Args:
            request: The FastAPI request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next handler
        """
        # Skip processing for excluded paths
        if not self.should_process(request):
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate processing time in milliseconds
        process_time = (time.time() - start_time) * 1000

        # Add timing header to response
        if self.header_name:
            response.headers[self.header_name] = f"{process_time:.2f}ms"

        # Log the timing
        self.log_request_time(
            path=request.url.path,
            method=request.method,
            time_ms=process_time,
            status_code=response.status_code,
        )

        # Call metrics handler if provided
        if self.metrics_handler:
            try:
                self.metrics_handler(request.url.path, process_time, request, response)
            except Exception as e:
                logger.error(f"Error in timing metrics handler: {e}")

        return response


def configure_timing(
    app: FastAPI,
    config: Optional[TimingConfig] = None,
    metrics_handler: Optional[Callable] = None,
    **kwargs,
) -> None:
    """
    Configure timing middleware for a FastAPI application.

    Args:
        app: The FastAPI application instance
        config: A TimingConfig instance with settings
        metrics_handler: Optional callback for custom metrics processing
        **kwargs: Additional settings to override config values

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.middleware import configure_timing, TimingConfig

        app = FastAPI()

        # Using default settings
        configure_timing(app)

        # Or with custom configuration
        timing_config = TimingConfig(
            header_name="X-Response-Time",
            log_level="info",
            log_threshold_ms=500  # Only log slow requests (>500ms)
        )
        configure_timing(app, timing_config)

        # With a custom metrics handler
        def my_metrics_handler(path, time_ms, request, response):
            # Send metrics to a monitoring system
            pass

        configure_timing(
            app,
            log_timing=True,
            metrics_handler=my_metrics_handler
        )
        ```
    """
    # Create default config if none provided
    if config is None:
        config = TimingConfig()

    # Get configuration parameters
    params = config.dict() if hasattr(config, "dict") else config.model_dump()
    params.update({k: v for k, v in kwargs.items() if v is not None})

    # Add the timing middleware
    app.add_middleware(TimingMiddleware, metrics_handler=metrics_handler, **params)
