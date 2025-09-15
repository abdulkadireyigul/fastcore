"""
Rate limiting middleware for FastAPI applications.

Provides both in-memory and Redis-based rate limiting middleware.

Limitations:
- Only global, IP-based rate limiting is supported (no per-route or user-based limits)
- Middleware is set up at startup, not dynamically per request
- Advanced features (e.g., custom backends, per-route config) are not included
"""

import time

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from fastcore.cache.manager import get_cache
from fastcore.config.base import BaseAppSettings
from fastcore.logging.manager import Logger


class BaseRateLimitMiddleware(BaseHTTPMiddleware):
    """Abstract base class for common rate-limiting logic."""

    def __init__(self, app, max_requests=60, window_seconds=60, logger=None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.logger = logger

    async def _get_count(self, key: str, window_seconds: int) -> int:
        """Abstract method: Increments the counter based on the backend."""
        raise NotImplementedError

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        now = int(time.time())
        window = now // self.window_seconds
        key = f"ratelimit:{ip}:{window}"

        count = await self._get_count(key, self.window_seconds)

        if count > self.max_requests:
            backend_name = self.__class__.__name__
            self.logger.warning(
                f"Rate limit exceeded for IP {ip} ({backend_name} backend): {count} requests in window {window}."
            )
            return Response("Too Many Requests", status_code=429)

        return await call_next(request)


class SimpleRateLimitMiddleware(BaseRateLimitMiddleware):
    """
    Simple IP-based rate limiting middleware (memory backend).

    Features:
    - Limits requests per IP per time window (memory only)
    - Configurable max_requests and window_seconds

    Limitations:
    - Only global, IP-based rate limiting is supported (no per-route or user-based limits)
    - Not suitable for production in distributed environments
    """

    def __init__(self, app, max_requests=60, window_seconds=60, logger=None):
        super().__init__(app, max_requests, window_seconds, logger)
        self.requests = {}
        logger.info(
            f"Initialized SimpleRateLimitMiddleware (memory) with max_requests={max_requests}, window_seconds={window_seconds}"
        )

    async def _get_count(self, key: str, window_seconds: int) -> int:
        self.requests.setdefault(key, 0)
        self.requests[key] += 1
        return self.requests[key]


class RedisRateLimitMiddleware(BaseRateLimitMiddleware):
    """
    Redis-based IP rate limiting middleware using the cache module.

    Features:
    - Limits requests per IP per time window (using Redis)
    - Configurable max_requests and window_seconds

    Limitations:
    - Only global, IP-based rate limiting is supported (no per-route or user-based limits)
    - Middleware is set up at startup, not dynamically per request
    - Advanced features (e.g., custom backends, per-route config) are not included
    """

    def __init__(self, app, max_requests=60, window_seconds=60, logger=None):
        super().__init__(app, max_requests, window_seconds, logger)
        self._memory_fallback = SimpleRateLimitMiddleware(
            self.app,
            max_requests=self.max_requests,
            window_seconds=self.window_seconds,
            logger=self.logger,
        )
        logger.info(
            f"Initialized RedisRateLimitMiddleware with max_requests={max_requests}, window_seconds={window_seconds}"
        )

    async def _get_count(self, key: str, window_seconds: int) -> int:
        try:
            cache = await get_cache()
            count = await cache.incr(key)
            if count == 1:
                await cache.expire(key, window_seconds)
            return count
        except Exception as e:
            self.logger.error(
                f"Rate limiting backend unavailable, falling back to memory: {e}"
            )
            return await self._memory_fallback._get_count(key, window_seconds)


def add_rate_limiting_middleware(
    app: FastAPI, settings: BaseAppSettings, logger: Logger
):
    """
    Adds rate limiting middleware to the application. Options and backend are loaded from config.
    """
    opts = getattr(
        settings, "RATE_LIMITING_OPTIONS", {"max_requests": 60, "window_seconds": 60}
    )
    backend = getattr(settings, "RATE_LIMITING_BACKEND", "memory")
    logger.info(
        f"Configuring rate limiting middleware with backend={backend}, options={opts}"
    )

    if backend == "redis":
        app.add_middleware(RedisRateLimitMiddleware, logger=logger, **opts)
        logger.debug("RedisRateLimitMiddleware added to FastAPI application.")
    else:
        app.add_middleware(SimpleRateLimitMiddleware, logger=logger, **opts)
        logger.debug("SimpleRateLimitMiddleware added to FastAPI application.")
