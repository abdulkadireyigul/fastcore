import logging
from typing import Optional

from fastapi import FastAPI

from fastcore.cache.backends import RedisCache
from fastcore.cache.base import BaseCache
from fastcore.config.base import BaseAppSettings
from fastcore.logging import Logger, ensure_logger

# Global cache instance
cache: Optional[BaseCache] = None


async def get_cache() -> BaseCache:
    """
    FastAPI dependency for retrieving the global cache instance.

    This function ensures that the cache is initialized before use.
    If the cache is not available (e.g., Redis connection failed during startup),
    it raises a RuntimeError. This allows decorators/callers to handle the
    failure (e.g., fail-silent fallback).

    Returns:
        BaseCache: The initialized cache instance.

    Raises:
        RuntimeError: If the cache has not been initialized.
    """
    if cache is None:
        raise RuntimeError("Cache not initialized")

    return cache


def setup_cache(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Configure the cache lifecycle for the FastAPI application.

    Registers startup and shutdown event handlers to initialize and close
    the Redis connection automatically.

    Args:
        app: The FastAPI application instance.
        settings: Application settings containing CACHE_URL, TTL, etc.
        logger: Optional logger instance. If None, a new one is configured.
    """
    # Initialize logger using the fastcore utility
    log: logging.Logger = ensure_logger(logger, __name__, settings)  # type: ignore

    url = settings.CACHE_URL
    ttl = settings.CACHE_DEFAULT_TTL
    prefix = settings.CACHE_KEY_PREFIX or ""

    async def init_cache() -> None:
        """Startup event handler: Initialize Redis connection."""
        global cache
        if cache is not None:
            return

        try:
            # Create and initialize the RedisBackend
            cache_instance = RedisCache(
                url=url, default_ttl=ttl, prefix=prefix, logger=log
            )
            await cache_instance.init()

            # Update global state
            cache = cache_instance

            # Attach to app state for easy access via request.app.state.cache
            app.state.cache = cache_instance

            log.info(f"RedisCache initialized successfully (url={url})")
        except Exception as e:
            # Fail-Silent Initialization:
            # If Redis fails, we log the error but do not crash the app startup.
            # The get_cache dependency will raise RuntimeError, which decorators can handle.
            cache = None
            log.error(f"RedisCache initialization failed: {e}")

    async def shutdown_cache() -> None:
        """Shutdown event handler: Close Redis connection."""
        global cache
        if cache:
            try:
                if hasattr(cache, "close"):
                    await cache.close()  # type: ignore
                log.info("RedisCache connection closed")
            except Exception as e:
                log.error(f"Error closing RedisCache: {e}")
            finally:
                cache = None

    # Register lifecycle handlers
    app.add_event_handler("startup", init_cache)
    app.add_event_handler("shutdown", shutdown_cache)
