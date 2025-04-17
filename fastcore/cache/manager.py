import logging
from typing import Optional

from fastapi import FastAPI

from ..config import BaseAppSettings
from .backends import RedisCache
from .base import BaseCache

# Module-level cache instance
cache: Optional[BaseCache] = None


async def get_cache() -> BaseCache:
    """
    FastAPI dependency for retrieving the cache instance.
    """
    if cache is None:
        raise RuntimeError("Cache not initialized")
    return cache


def setup_cache(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Configure cache lifecycle for FastAPI application.

    - On startup: initialize RedisCache
    - On shutdown: close Redis connection
    - Provides get_cache dependency
    """
    log = logger or logging.getLogger(__name__)
    url = settings.CACHE_URL
    ttl = settings.CACHE_DEFAULT_TTL
    prefix = settings.CACHE_KEY_PREFIX or ""

    async def init_cache():
        global cache
        cache = RedisCache(url=url, default_ttl=ttl, prefix=prefix, logger=log)
        await cache.init()
        log.info(f"RedisCache initialized (url={url})")

    async def shutdown_cache():
        if cache:
            await cache.close()
            log.info("RedisCache closed")

    app.add_event_handler("startup", init_cache)
    app.add_event_handler("shutdown", shutdown_cache)
