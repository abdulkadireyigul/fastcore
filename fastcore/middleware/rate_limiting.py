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

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from fastcore.cache.manager import get_cache
from fastcore.config.base import BaseAppSettings
from fastcore.logging.manager import Logger


class BaseRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Base class for rate limiting middleware implementations.

    Provides common functionality for route pattern matching and configuration.

    Features:
    - Pattern matching for dynamic routes (e.g., /api/users/{id})
    - Per-route rate limiting configuration
    - HTTP method-specific rate limits
    - Supports all FastAPI path parameter types (int, float, path)
    """

    def __init__(
        self, app, max_requests=60, window_seconds=60, logger=None, route_config=None
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.logger = logger
        # Normalize route configs to handle method-specific limits
        self.route_config = self._normalize_route_config(route_config or {})
        # Compile regex patterns for route matching
        self._compile_route_patterns()

    def _normalize_route_config(self, configs):
        """
        Normalize route configurations to support method-specific limits.

        Examples of valid configurations:
        {
            "/api/items/{item_id}": {
                "max_requests": 100,  # Applies to all methods
                "window_seconds": 60
            },
            "/api/users": {
                "GET": {"max_requests": 1000},  # Method-specific
                "POST": {"max_requests": 50},
                "enabled": False  # Global flag for the route
            }
        }
        """
        normalized = {}
        for path, config in configs.items():
            if any(
                k.upper()
                in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
                for k in config.keys()
            ):
                # Config already has method-specific settings
                normalized[path] = {
                    method.upper(): method_config
                    for method, method_config in config.items()
                    if method.upper()
                    in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
                }
                # Preserve non-method keys (like 'enabled')
                for key, value in config.items():
                    if key.upper() not in [
                        "GET",
                        "POST",
                        "PUT",
                        "DELETE",
                        "PATCH",
                        "HEAD",
                        "OPTIONS",
                    ]:
                        normalized[path][key] = value
            else:
                # Apply config to all methods
                normalized[path] = config

        return normalized

    def _compile_route_patterns(self):
        """Pre-compile regex patterns for route matching."""
        self._route_patterns = {}
        for pattern, config in self.route_config.items():
            if "{" in pattern:
                # Convert FastAPI path params to regex
                regex_pattern = pattern.replace("/", "\\/")

                # Handle typed parameters (e.g., {param:int})
                regex_pattern = re.sub(
                    r"{([^:}]+):int}", r"(?P<\1>\\d+)", regex_pattern
                )

                # Handle typed parameters (e.g., {param:float})
                regex_pattern = re.sub(
                    r"{([^:}]+):float}", r"(?P<\1>[+-]?\\d*\\.?\\d+)", regex_pattern
                )

                # Handle typed parameters (e.g., {param:path})
                regex_pattern = re.sub(r"{([^:}]+):path}", r"(?P<\1>.+)", regex_pattern)

                # Handle any remaining untyped parameters (e.g., {param})
                regex_pattern = re.sub(r"{([^}]+)}", r"(?P<\1>[^/]+)", regex_pattern)

                self._route_patterns[pattern] = (
                    re.compile(f"^{regex_pattern}$"),
                    config,
                )

    def _match_route_pattern(self, path: str, method: str = "") -> dict:
        """
        Match path against route patterns and return matching config.

        If method is provided, tries to get method-specific configuration first,
        then falls back to general route configuration.
        """
        # First try exact match
        if path in self.route_config:
            config = self.route_config[path]
            if method and method.upper() in config:
                # Merge method-specific config with general config
                return {**config, **config[method.upper()]}
            return config

        # Then try pattern matching
        for pattern, (regex, config) in self._route_patterns.items():
            if regex.match(path):
                if self.logger:
                    self.logger.debug(f"Path {path} matched pattern {pattern}")
                if method and method.upper() in config:
                    # Merge method-specific config with general config
                    return {**config, **config[method.upper()]}
                return config

        return {}


class SimpleRateLimitMiddleware(BaseRateLimitMiddleware):
    """
    Simple IP-based rate limiting middleware (memory backend).

    Features:
    - Limits requests per IP per time window (memory only)
    - Configurable max_requests and window_seconds
    - Supports dynamic path patterns (e.g., "/dzi/{slide_id}_files/{level}/{col}_{row}.jpeg")

    Limitations:
    - Not suitable for production in distributed environments
    """

    def __init__(
        self, app, max_requests=60, window_seconds=60, logger=None, route_config=None
    ):
        super().__init__(app, max_requests, window_seconds, logger, route_config)
        self.requests = {}
        logger.info(
            f"Initialized SimpleRateLimitMiddleware (memory) with max_requests={max_requests}, window_seconds={window_seconds}"
        )

    async def dispatch(self, request: Request, call_next):
        # Get route specific config if exists, including method-specific config
        route_config = self._match_route_pattern(request.url.path, request.method)

        # Check if rate limiting is disabled for this route
        if route_config.get("enabled") is False:
            return await call_next(request)

        # Get route specific limits or use defaults
        max_requests = route_config.get("max_requests", self.max_requests)
        window_seconds = route_config.get("window_seconds", self.window_seconds)

        ip = request.client.host
        method = request.method
        now = int(time.time())
        window = now // window_seconds
        key = f"{ip}:{method}:{request.url.path}:{window}"
        self.requests.setdefault(key, 0)
        self.requests[key] += 1
        if self.requests[key] > max_requests:
            self.logger.warning(
                f"Rate limit exceeded for IP {ip} on path {request.url.path} (memory backend): {self.requests[key]} requests in window {window}"
            )
            return Response("Too Many Requests", status_code=429)
        return await call_next(request)


class RedisRateLimitMiddleware(BaseRateLimitMiddleware):
    """
    Redis-based IP rate limiting middleware using the cache module.

    Features:
    - Limits requests per IP per time window (using Redis)
    - Configurable max_requests and window_seconds
    - Supports dynamic path patterns (e.g., "/api/items/{item_id}")
    - Falls back to memory backend if Redis is unavailable
    """

    def __init__(
        self, app, max_requests=60, window_seconds=60, logger=None, route_config=None
    ):
        super().__init__(app, max_requests, window_seconds, logger, route_config)
        logger.info(
            f"Initialized RedisRateLimitMiddleware with max_requests={max_requests}, window_seconds={window_seconds}"
        )

    async def dispatch(self, request: Request, call_next):
        # Get route specific config if exists, including pattern matching
        route_config = self._match_route_pattern(request.url.path, request.method)

        # Check if rate limiting is disabled for this route
        if route_config.get("enabled") is False:
            return await call_next(request)

        # Get route specific limits or use defaults
        max_requests = route_config.get("max_requests", self.max_requests)
        window_seconds = route_config.get("window_seconds", self.window_seconds)

        ip = request.client.host
        method = request.method
        now = int(time.time())
        window = now // window_seconds
        key = f"ratelimit:{ip}:{method}:{request.url.path}:{window}"
        try:
            cache = await get_cache()
            count = await cache.incr(key)
            if count == 1:
                await cache.expire(key, window_seconds)
            if count > max_requests:
                self.logger.warning(
                    f"Rate limit exceeded for IP {ip} on path {request.url.path} (redis backend): {count} requests in window {window}"
                )
                return Response("Too Many Requests", status_code=429)
            return await call_next(request)
        except Exception as e:
            self.logger.error(
                f"Rate limiting backend unavailable, falling back to memory: {e}"
            )
            # Memory fallback
            if not hasattr(self, "_memory_fallback"):
                self._memory_fallback = SimpleRateLimitMiddleware(
                    self.app,
                    max_requests=self.max_requests,
                    window_seconds=self.window_seconds,
                    logger=self.logger,
                    route_config=self.route_config,
                )
            return await self._memory_fallback.dispatch(request, call_next)


def add_rate_limiting_middleware(
    app: FastAPI, settings: BaseAppSettings, logger: Logger
):
    """
    Adds rate limiting middleware to the application. Options and backend are loaded from config.
    """
    opts = getattr(
        settings, "RATE_LIMITING_OPTIONS", {"max_requests": 60, "window_seconds": 60}
    )
    # Extract route configs but don't remove from opts to maintain backward compatibility
    route_config = opts.get("route_config", {})
    backend = getattr(settings, "RATE_LIMITING_BACKEND", "memory")
    logger.info(
        f"Configuring rate limiting middleware with backend={backend}, options={opts}"
    )

    middleware_opts = opts.copy()
    if route_config:
        middleware_opts["route_config"] = route_config
    if backend == "redis":
        app.add_middleware(RedisRateLimitMiddleware, logger=logger, **middleware_opts)
        logger.debug("RedisRateLimitMiddleware added to FastAPI application.")
    else:
        app.add_middleware(SimpleRateLimitMiddleware, logger=logger, **middleware_opts)
        logger.debug("SimpleRateLimitMiddleware added to FastAPI application.")
