import sys
import time

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from fastcore.cache.manager import get_cache
from fastcore.config.base import BaseAppSettings
from fastcore.logging.manager import Logger


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple IP-based rate limiting middleware (memory backend).
    Can be extended with Redis or other backends for production use.
    """

    def __init__(self, app, max_requests=60, window_seconds=60, logger=None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
        self.logger = logger
        logger.info(
            f"Initialized SimpleRateLimitMiddleware (memory) with max_requests={max_requests}, window_seconds={window_seconds}"
        )

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        now = int(time.time())
        window = now // self.window_seconds
        key = f"{ip}:{window}"
        self.requests.setdefault(key, 0)
        self.requests[key] += 1
        if self.requests[key] > self.max_requests:
            self.logger.warning(
                f"Rate limit exceeded for IP {ip} (memory backend): {self.requests[key]} requests in window {window}"
            )
            return Response("Too Many Requests", status_code=429)
        return await call_next(request)


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based IP rate limiting middleware using the cache module.
    """

    def __init__(self, app, max_requests=60, window_seconds=60, logger=None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.logger = logger
        logger.info(
            f"Initialized RedisRateLimitMiddleware with max_requests={max_requests}, window_seconds={window_seconds}"
        )

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        now = int(time.time())
        window = now // self.window_seconds
        key = f"ratelimit:{ip}:{window}"
        try:
            cache = await get_cache()
            count = await cache.incr(key)
            if count == 1:
                await cache.expire(key, self.window_seconds)
            if count > self.max_requests:
                self.logger.warning(
                    f"Rate limit exceeded for IP {ip} (redis backend): {count} requests in window {window}"
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
