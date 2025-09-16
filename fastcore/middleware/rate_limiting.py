"""
Rate limiting middleware for FastAPI applications.

Provides both in-memory and Redis-based rate limiting middleware.

Limitations:
- Only global, IP-based rate limiting is supported (no per-route or user-based limits)
- Middleware is set up at startup, not dynamically per request
- Advanced features (e.g., custom backends, per-route config) are not included
"""

import re
import time
from typing import Tuple

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from fastcore.cache.manager import get_cache
from fastcore.config.base import BaseAppSettings
from fastcore.errors.handlers import http_exception_handler
from fastcore.logging.manager import Logger


class BaseRateLimitMiddleware(BaseHTTPMiddleware):
    """Abstract base class for common rate-limiting logic with route-based support."""

    def __init__(
        self, app, max_requests=60, window_seconds=60, logger=None, routes=None
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.logger = logger
        self.routes = routes or {}

        # Compile regex patterns for dynamic routes
        self._compiled_patterns = {}
        for pattern, config in self.routes.items():
            # Handle method-specific patterns: "GET:/api/users" or just "/api/users"
            if ":" in pattern and pattern.split(":", 1)[0] in [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "PATCH",
                "HEAD",
                "OPTIONS",
            ]:
                method, path_pattern = pattern.split(":", 1)
                # regex_pattern = f"{method}:{self._fastapi_to_regex(path_pattern)}"
                regex_pattern = self._fastapi_to_regex(path_pattern)
                self._compiled_patterns[f"{method}:{regex_pattern}"] = config
            else:
                # regex_pattern = self._fastapi_to_regex(pattern)
                regex_pattern = self._fastapi_to_regex(pattern)
                self._compiled_patterns[regex_pattern] = config
            # self._compiled_patterns[regex_pattern] = config

    def _fastapi_to_regex(self, pattern: str) -> str:
        """Convert FastAPI path pattern to regex pattern."""
        # Replace FastAPI path parameters with regex groups
        # {param} -> ([^/]+)
        # {param:int} -> (\d+)
        # {param:float} -> ([\d.]+)
        pattern = re.sub(r"\{[^}]+:int\}", r"(\\d+)", pattern)
        pattern = re.sub(r"\{[^}]+:float\}", r"([\\d.]+)", pattern)
        pattern = re.sub(r"\{[^}]+\}", r"([^/]+)", pattern)
        # Escape special regex characters except our replacements
        pattern = pattern.replace(".", "\\.")
        return f"^{pattern}$"

    def _get_route_config(self, method: str, path: str) -> Tuple[int, int, bool]:
        """Get rate limiting config for specific route and method."""
        # Try method-specific config first: "GET:/api/users"
        method_path = f"{method}:{path}"
        if method_path in self.routes:
            config = self.routes[method_path]
            return (
                config.get("max_requests", self.max_requests),
                config.get("window_seconds", self.window_seconds),
                config.get("disabled", False),
            )

        # Check exact path match (any method)
        if path in self.routes:
            config = self.routes[path]
            return (
                config.get("max_requests", self.max_requests),
                config.get("window_seconds", self.window_seconds),
                config.get("disabled", False),
            )

        # Check regex patterns for dynamic routes with method
        method_pattern = f"{method}:"
        for pattern, config in self._compiled_patterns.items():
            if pattern.startswith(method_pattern) and re.match(
                pattern[len(method_pattern) :], path
            ):
                return (
                    config.get("max_requests", self.max_requests),
                    config.get("window_seconds", self.window_seconds),
                    config.get("disabled", False),
                )

        # Check regex patterns for dynamic routes (any method)
        for pattern, config in self._compiled_patterns.items():
            if not ":" in pattern and re.match(pattern, path):
                return (
                    config.get("max_requests", self.max_requests),
                    config.get("window_seconds", self.window_seconds),
                    config.get("disabled", False),
                )

        # Return default config
        return self.max_requests, self.window_seconds, False

    async def _get_count(self, key: str, window_seconds: int) -> int:
        """Abstract method: Increments the counter based on the backend."""
        raise NotImplementedError

    async def dispatch(self, request: Request, call_next):
        try:
            # Get route-specific configuration
            method = request.method
            path = request.url.path
            max_requests, window_seconds, disabled = self._get_route_config(
                method, path
            )

            # Skip rate limiting if disabled for this route
            if disabled:
                return await call_next(request)

            ip = request.client.host
            now = int(time.time())
            window = now // window_seconds
            key = f"ratelimit:{ip}:{method}:{path}:{window}"  # Include method and path for route-specific limiting

            count = await self._get_count(key, window_seconds)

            if count > max_requests:
                backend_name = self.__class__.__name__
                self.logger.warning(
                    f"Rate limit exceeded for IP {ip} on {method} {path} ({backend_name} backend): {count}/{max_requests} requests in window {window}."
                )
                return Response("Too Many Requests", status_code=429)

            return await call_next(request)

        except Exception as e:
            self.logger.error(f"Rate limiting dispatch failed: {e}", exc_info=True)
            return await http_exception_handler(request, e, self.logger)


class SimpleRateLimitMiddleware(BaseRateLimitMiddleware):
    """
    Simple IP-based rate limiting middleware (memory backend) with route-based support.

    Features:
    - Limits requests per IP per time window per route (memory only)
    - Configurable max_requests and window_seconds per route
    - Can disable rate limiting for specific routes

    Limitations:
    - Not suitable for production in distributed environments
    """

    def __init__(
        self, app, max_requests=60, window_seconds=60, routes=None, logger=None
    ):
        super().__init__(app, max_requests, window_seconds, logger, routes)
        self.requests = {}
        logger.info(
            f"Initialized SimpleRateLimitMiddleware (memory) with max_requests={max_requests}, window_seconds={window_seconds}, routes={routes}"
        )

    async def _get_count(self, key: str, window_seconds: int) -> int:
        self.requests.setdefault(key, 0)
        self.requests[key] += 1
        return self.requests[key]


class RedisRateLimitMiddleware(BaseRateLimitMiddleware):
    """
    Redis-based IP rate limiting middleware using the cache module with route-based support.

    Features:
    - Limits requests per IP per time window per route (using Redis)
    - Configurable max_requests and window_seconds per route
    - Can disable rate limiting for specific routes

    Limitations:
    - Advanced features (e.g., custom backends, per-route config) are not included
    """

    def __init__(
        self, app, max_requests=60, window_seconds=60, routes=None, logger=None
    ):
        super().__init__(app, max_requests, window_seconds, logger, routes)
        self._memory_fallback = SimpleRateLimitMiddleware(
            self.app,
            max_requests=self.max_requests,
            window_seconds=self.window_seconds,
            logger=self.logger,
            routes=routes,
        )
        logger.info(
            f"Initialized RedisRateLimitMiddleware with max_requests={max_requests}, window_seconds={window_seconds}, routes={routes}"
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
    Adds rate limiting middleware to the application. Options, backend and route configs are loaded from config.

    Example settings:
    RATE_LIMITING_BACKEND = "redis"  # or "memory"
    RATE_LIMITING_OPTIONS = {
        "max_requests": 60,
        "window_seconds": 60,
        "routes": {
            # Method-specific configs
            "POST:/api/users": {"max_requests": 10, "window_seconds": 60},
            "GET:/api/users": {"max_requests": 100, "window_seconds": 60},

            # Any method for this endpoint
            "/api/heavy-endpoint": {"max_requests": 10, "window_seconds": 60},

            # Dynamic routes with method
            "GET:/dzi/{slide_id}_files/{level:int}/{col:int}_{row:int}.jpeg": {"max_requests": 1000, "window_seconds": 60},

            # Disable completely for any method
            "/api/no-limit": {"disabled": True}
        }
    }
    """
    opts = getattr(
        settings,
        "RATE_LIMITING_OPTIONS",
        {"max_requests": 60, "window_seconds": 60, "routes": None},
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
