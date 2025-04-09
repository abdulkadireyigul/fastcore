"""
Rate limiting middleware for FastAPI applications.

This module provides rate limiting capabilities to control the number of requests
clients can make to your API within specified time windows.
"""

import time
from datetime import timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from fastcore.logging import get_logger

logger = get_logger(__name__)


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""

    limit: int = Field(
        default=100,
        description="Maximum number of requests allowed within the time window",
    )
    window_seconds: int = Field(default=60, description="Time window in seconds")
    block_duration_seconds: int = Field(
        default=300, description="Duration in seconds to block after limit is exceeded"
    )
    key_func: Optional[str] = Field(
        default=None,
        description="Name of function to use for generating cache keys (default: uses client IP)",
    )
    exclude_paths: List[str] = Field(
        default=[], description="List of paths to exclude from rate limiting"
    )

    @validator("window_seconds", "block_duration_seconds")
    def validate_positive(cls, v):
        """Ensure time values are positive."""
        if v <= 0:
            raise ValueError("Time values must be positive")
        return v


class SimpleMemoryStore:
    """
    Simple in-memory store for rate limiting data.

    Warning:
        This is a basic implementation for simplicity. In production,
        consider using Redis or another distributed store for rate limiting
        data, especially in multi-server deployments.
    """

    def __init__(self):
        """Initialize the memory store."""
        self.requests: Dict[str, List[float]] = {}
        self.blocked: Dict[str, float] = {}

    def add_request(self, key: str, timestamp: float = None) -> None:
        """
        Add a request timestamp for a key.

        Args:
            key: The client identifier key
            timestamp: The request timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()

        if key not in self.requests:
            self.requests[key] = []

        self.requests[key].append(timestamp)

    def get_requests(self, key: str, window_seconds: int) -> List[float]:
        """
        Get recent requests within the time window.

        Args:
            key: The client identifier key
            window_seconds: The time window in seconds

        Returns:
            List of request timestamps within the window
        """
        if key not in self.requests:
            return []

        # Use mocked time to match test expectations
        now = time.time()
        window_start = now - window_seconds

        # Filter requests to only include those within the window
        recent_requests = [ts for ts in self.requests[key] if ts >= window_start]

        return recent_requests

    def block(self, key: str, duration_seconds: int) -> None:
        """
        Block a client for a specified duration.

        Args:
            key: The client identifier key
            duration_seconds: The duration to block in seconds
        """
        self.blocked[key] = time.time() + duration_seconds
        logger.warning(
            f"Rate limit exceeded. Client {key} blocked for {duration_seconds} seconds"
        )

    def is_blocked(self, key: str) -> bool:
        """
        Check if a client is currently blocked.

        Args:
            key: The client identifier key

        Returns:
            True if the client is blocked, False otherwise
        """
        now = time.time()

        if key not in self.blocked:
            return False

        # Check if block has expired
        if self.blocked[key] <= now:
            # Remove expired block
            del self.blocked[key]
            return False

        return True

    def get_block_remaining(self, key: str) -> int:
        """
        Get remaining block time in seconds.

        Args:
            key: The client identifier key

        Returns:
            Remaining block time in seconds, or 0 if not blocked
        """
        if not self.is_blocked(key):
            return 0

        return int(self.blocked[key] - time.time())


def get_client_ip(request: Request) -> str:
    """
    Get the client IP address from a request.

    Args:
        request: The FastAPI request

    Returns:
        The client IP address as a string
    """
    # Check for forwarded IP (e.g., behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Use the first IP in case of multiple proxies
        return forwarded.split(",")[0].strip()

    # Fall back to direct client IP
    client_host = request.client.host if request.client else "unknown"
    return client_host


class RateLimiter(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.

    This middleware limits the number of requests a client can make
    within a specified time window.
    """

    def __init__(
        self,
        app: ASGIApp,
        limit: int = 100,
        window_seconds: int = 60,
        block_duration_seconds: int = 300,
        key_func: Optional[Callable[[Request], str]] = None,
        store: Any = None,
        exclude_paths: List[str] = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            app: The ASGI application
            limit: Maximum number of requests allowed within the time window
            window_seconds: Time window in seconds
            block_duration_seconds: Duration to block after exceeding the limit
            key_func: Function to generate cache keys (defaults to client IP)
            store: Storage backend for rate limiting data (defaults to SimpleMemoryStore)
            exclude_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.block_duration_seconds = block_duration_seconds
        self.key_func = key_func or get_client_ip
        self.store = store or SimpleMemoryStore()
        self.exclude_paths = exclude_paths or []

        # Log configuration
        logger.info(
            f"Rate limiter configured with limit={limit} "
            f"requests per {window_seconds} seconds"
        )

    def should_exempt(self, request: Request) -> bool:
        """
        Check if a request should be exempted from rate limiting.

        Args:
            request: The FastAPI request

        Returns:
            True if the request should be exempted, False otherwise
        """
        # Always allow OPTIONS requests (pre-flight requests)
        if request.method == "OPTIONS":
            return True

        # Check against excluded paths
        path = request.url.path
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True

        return False

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request with rate limiting.

        Args:
            request: The FastAPI request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next handler, or a 429 response if rate limited
        """
        # Skip rate limiting for exempted requests
        if self.should_exempt(request):
            return await call_next(request)

        # Generate the client key
        client_key = self.key_func(request)

        # Check if client is blocked
        if self.store.is_blocked(client_key):
            remaining = self.store.get_block_remaining(client_key)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests", "retry_after": remaining},
                headers={"Retry-After": str(remaining)},
            )

        # Get recent requests for this client
        recent_requests = self.store.get_requests(client_key, self.window_seconds)

        # Check if limit is exceeded
        if len(recent_requests) >= self.limit:
            # Block the client
            self.store.block(client_key, self.block_duration_seconds)

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests",
                    "retry_after": self.block_duration_seconds,
                },
                headers={"Retry-After": str(self.block_duration_seconds)},
            )

        # Record this request
        self.store.add_request(client_key)

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to response
        requests_count = len(recent_requests) + 1
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.limit - requests_count)
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time() + self.window_seconds)
        )

        return response


def configure_rate_limiting(
    app: FastAPI, config: Optional[RateLimitConfig] = None, store: Any = None, **kwargs
) -> None:
    """
    Configure rate limiting middleware for a FastAPI application.

    Args:
        app: The FastAPI application instance
        config: A RateLimitConfig instance with rate limiting settings
        store: Storage backend for rate limiting data (defaults to SimpleMemoryStore)
        **kwargs: Additional rate limiting settings to override config values

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.middleware import configure_rate_limiting, RateLimitConfig

        app = FastAPI()

        # Using default settings (100 requests per minute)
        configure_rate_limiting(app)

        # Or with custom configuration
        rate_limit_config = RateLimitConfig(
            limit=50,
            window_seconds=3600,  # 50 requests per hour
            exclude_paths=["/docs", "/redoc", "/openapi.json"]
        )
        configure_rate_limiting(app, rate_limit_config)

        # Or with direct keyword arguments
        configure_rate_limiting(
            app,
            limit=200,
            window_seconds=10,
            exclude_paths=["/health"]
        )
        ```
    """
    # Create default config if none provided
    if config is None:
        config = RateLimitConfig()

    # Get configuration parameters - handle Pydantic v1 and v2
    if hasattr(config, "model_dump"):
        params = config.model_dump()
    else:
        params = config.dict()

    params.update({k: v for k, v in kwargs.items() if v is not None})

    # Extract key_func name if provided
    key_func_name = params.pop("key_func", None)
    key_func = None

    # Use the specified key function if provided
    if key_func_name == "get_client_ip":
        key_func = get_client_ip

    # Add the rate limiting middleware
    app.add_middleware(RateLimiter, key_func=key_func, store=store, **params)
