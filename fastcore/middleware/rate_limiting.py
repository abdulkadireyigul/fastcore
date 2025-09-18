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
from collections import OrderedDict
from functools import lru_cache
from typing import Tuple

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

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

        # Pre-compile and optimize pattern storage
        self._exact_routes = {}  # Direct path lookups
        self._method_exact_routes = {}  # Method:path lookups
        self._dynamic_patterns = []  # Compiled regex patterns

        self._prepare_routes()

    def _prepare_routes(self):
        """Separate exact routes from dynamic patterns for faster lookups."""
        for pattern, config in self.routes.items():
            # Handle method-specific patterns
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

                # Check if it's a dynamic route (contains {})
                if "{" in path_pattern:
                    regex = self._fastapi_to_regex(path_pattern)
                    compiled = re.compile(regex)
                    self._dynamic_patterns.append((method, compiled, config))
                else:
                    # Exact method:path match
                    self._method_exact_routes[f"{method}:{path_pattern}"] = config
            else:
                # Check if it's a dynamic route
                if "{" in pattern:
                    regex = self._fastapi_to_regex(pattern)
                    compiled = re.compile(regex)
                    self._dynamic_patterns.append((None, compiled, config))
                else:
                    # Exact path match (any method)
                    self._exact_routes[pattern] = config

    def _fastapi_to_regex(self, pattern: str) -> str:
        """Convert FastAPI path pattern to regex pattern."""
        pattern = re.sub(r"\{[^}]+:int\}", r"(\\d+)", pattern)
        pattern = re.sub(r"\{[^}]+:float\}", r"([\\d.]+)", pattern)
        pattern = re.sub(r"\{[^}]+\}", r"([^/]+)", pattern)
        pattern = pattern.replace(".", "\\.")
        return f"^{pattern}$"

    @lru_cache(maxsize=1024)
    def _get_route_config(self, method: str, path: str) -> Tuple[int, int, bool]:
        """
        Cached route config lookup to avoid repeated pattern matching.
        LRU cache will store the 1024 most recently used method+path combinations.
        """
        # Try method-specific exact match first
        method_path = f"{method}:{path}"
        if method_path in self._method_exact_routes:
            config = self._method_exact_routes[method_path]
            return (
                config.get("max_requests", self.max_requests),
                config.get("window_seconds", self.window_seconds),
                config.get("disabled", False),
            )

        # Try exact path match (any method)
        if path in self._exact_routes:
            config = self._exact_routes[path]
            return (
                config.get("max_requests", self.max_requests),
                config.get("window_seconds", self.window_seconds),
                config.get("disabled", False),
            )

        # Check dynamic patterns (already compiled)
        for pattern_method, compiled_regex, config in self._dynamic_patterns:
            # Check if method matches (if specified)
            if pattern_method and pattern_method != method:
                continue

            if compiled_regex.match(path):
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
            # key = f"ratelimit:{ip}:{method}:{path}:{window}"  # Include method and path for route-specific limiting

            # Simplified key structure for better performance
            # Use hash of path for dynamic routes to avoid key explosion
            path_key = str(
                hash(f"{method}:{path}") % 10000
            )  # Bucket paths into 10000 groups
            key = f"rl:{ip}:{path_key}:{window}"

            count = await self._get_count(key, window_seconds)

            if count > max_requests:
                backend_name = self.__class__.__name__
                self.logger.warning(
                    f"Rate limit exceeded for IP {ip} on {method} {path} ({backend_name} backend): {count}/{max_requests} requests in window {window}."
                )

                # Add headers to the 429 response before returning
                headers = {
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str((window + 1) * window_seconds),
                }

                return Response("Too Many Requests", status_code=429, headers=headers)

            # return await call_next(request)

            response = await call_next(request)

            # Add rate limit headers
            if isinstance(response, Response):
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = str(
                    max(0, max_requests - count)
                )
                response.headers["X-RateLimit-Reset"] = str(
                    (window + 1) * window_seconds
                )

            return response

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
        self,
        app,
        max_requests=60,
        window_seconds=60,
        routes=None,
        logger=None,
        max_cache_size=10000,
        cleanup_interval=300,
    ):
        super().__init__(app, max_requests, window_seconds, logger, routes)
        self.requests = OrderedDict()
        self.max_cache_size = max_cache_size
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()

        logger.info(
            f"Initialized SimpleRateLimitMiddleware (memory) with max_requests={max_requests}, window_seconds={window_seconds}, routes={routes}"
        )

    def _cleanup_old_entries(self):
        """Remove expired entries to prevent memory leak."""
        current_time = time.time()
        current_window = int(current_time) // self.window_seconds

        # Only cleanup periodically
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        self.last_cleanup = current_time

        # Remove entries from old windows
        keys_to_remove = []
        for key in list(self.requests.keys()):
            # Extract window from key (format: "rl:ip:path_hash:window")
            try:
                window = int(key.split(":")[-1])
                if window < current_window - 1:  # Keep current and previous window
                    keys_to_remove.append(key)
            except (ValueError, IndexError):
                # Invalid key format, remove it
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self.requests.pop(key, None)

        # Enforce max cache size (LRU eviction)
        while len(self.requests) > self.max_cache_size:
            self.requests.popitem(last=False)  # Remove oldest

    async def _get_count(self, key: str, window_seconds: int) -> int:
        # self.requests.setdefault(key, 0)
        # Periodic cleanup
        self._cleanup_old_entries()

        # Get or initialize counter
        if key not in self.requests:
            self.requests[key] = 0
            # Move to end (most recently used)
            self.requests.move_to_end(key)

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
        self.cache = None
        self._memory_fallback = SimpleRateLimitMiddleware(
            self.app,
            max_requests=self.max_requests,
            window_seconds=self.window_seconds,
            logger=self.logger,
            routes=routes,
            max_cache_size=5000,  # Smaller cache for fallback
            cleanup_interval=60,  # More aggressive cleanup
        )
        logger.info(
            f"Initialized RedisRateLimitMiddleware with max_requests={max_requests}, window_seconds={window_seconds}, routes={routes}"
        )

    async def _get_count(self, key: str, window_seconds: int) -> int:
        try:
            if self.cache is None:
                self.cache = await get_cache()
            # cache = await get_cache()
            # count = await cache.incr(key)
            # if count == 1:
            #     await cache.expire(key, window_seconds + 10)

            # Use the new atomic incr_with_expire method
            count = await self.cache.incr_with_expire(key, ttl=window_seconds + 10)

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
