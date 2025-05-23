import sys
from typing import Optional

from fastapi import FastAPI

from fastcore.cache.backends import RedisCache
from fastcore.cache.base import BaseCache
from fastcore.config.base import BaseAppSettings
from fastcore.logging import Logger, ensure_logger

# Module-level cache instance
cache: Optional[BaseCache] = None


async def get_cache() -> Optional[BaseCache]:
    """
    FastAPI dependency for retrieving the cache instance.

    Only Redis backend is supported. Only async cache operations are available.
    Raises RuntimeError if cache is not initialized (e.g., Redis unavailable).
    """
    manager_mod = sys.modules.get("fastcore.cache.manager")
    cache_instance = getattr(manager_mod, "cache", None)
    if cache_instance is None:
        raise RuntimeError("Cache not initialized")

    return cache_instance


def setup_cache(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Configure cache lifecycle for FastAPI application.

    - On startup: initialize RedisCache (async only)
    - On shutdown: close Redis connection
    - Provides get_cache dependency

    Limitations:
    - Only Redis backend is supported (no in-memory fallback)
    - Only async cache operations are available
    - No fallback if Redis is unavailable
    """
    log = ensure_logger(logger, __name__, settings)
    url = settings.CACHE_URL
    ttl = settings.CACHE_DEFAULT_TTL
    prefix = settings.CACHE_KEY_PREFIX or ""

    async def init_cache():
        global cache
        try:
            cache = RedisCache(url=url, default_ttl=ttl, prefix=prefix, logger=log)
            await cache.init()
            log.info(f"RedisCache initialized (url={url})")
        except Exception as e:
            cache = None
            log.error(f"RedisCache initialization failed: {e}")

    async def shutdown_cache():
        if cache:
            await cache.close()
            log.info("RedisCache closed")

    app.add_event_handler("startup", init_cache)
    app.add_event_handler("shutdown", shutdown_cache)
