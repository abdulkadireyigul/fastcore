"""
Unit tests for the cache.manager module.

Covers:
- Setup of cache for FastAPI
- Event handlers (startup/shutdown)
- Cache initialization and dependency injection
- Error handling
"""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from fastcore.cache.manager import get_cache, setup_cache


@pytest.fixture
def reset_module_cache():
    """Reset module-level cache for each test."""
    import fastcore.cache.manager as manager_module

    original_cache = manager_module.cache
    manager_module.cache = None
    yield
    manager_module.cache = original_cache


@pytest.fixture
def mock_app():
    """Mock FastAPI app."""
    app = MagicMock(spec=FastAPI)
    app.add_event_handler = MagicMock()
    app.router = MagicMock()
    app.router.on_startup = []
    app.router.on_shutdown = []

    # Capture event handlers
    def add_event_handler(event, func):
        if event == "startup":
            app.router.on_startup.append(func)
        elif event == "shutdown":
            app.router.on_shutdown.append(func)

    app.add_event_handler.side_effect = add_event_handler
    return app


@pytest.fixture
def mock_settings():
    """Mock app settings."""
    settings = MagicMock()
    settings.CACHE_URL = "redis://localhost:6379/0"
    settings.CACHE_DEFAULT_TTL = 300
    settings.CACHE_KEY_PREFIX = "test:"
    return settings


def test_get_cache_not_initialized(reset_module_cache):
    """Test that get_cache raises an error when cache is not initialized."""
    with pytest.raises(RuntimeError, match="Cache not initialized"):
        import asyncio

        asyncio.run(get_cache())


def test_setup_cache_registers_event_handlers(mock_app, mock_settings):
    """Test that setup_cache registers the correct event handlers."""
    setup_cache(mock_app, mock_settings)

    # Verify event handlers were registered
    mock_app.add_event_handler.assert_any_call("startup", mock_app.router.on_startup[0])
    mock_app.add_event_handler.assert_any_call(
        "shutdown", mock_app.router.on_shutdown[0]
    )


@pytest.mark.asyncio
async def test_init_cache_on_startup(mock_app, mock_settings, reset_module_cache):
    """Test that the init_cache event handler initializes the cache correctly."""
    with patch("fastcore.cache.manager.RedisCache") as mock_redis_cache:
        # Setup mock Redis cache
        mock_instance = AsyncMock()
        mock_redis_cache.return_value = mock_instance

        # Setup cache
        setup_cache(mock_app, mock_settings)

        # Call startup event handler
        startup_handler = mock_app.router.on_startup[0]
        await startup_handler()

        # Verify Redis cache was initialized correctly
        mock_redis_cache.assert_called_once_with(
            url=mock_settings.CACHE_URL,
            default_ttl=mock_settings.CACHE_DEFAULT_TTL,
            prefix=mock_settings.CACHE_KEY_PREFIX,
            logger=ANY,
        )
        mock_instance.init.assert_awaited_once()

        # Verify cache is now accessible
        import fastcore.cache.manager as manager_module

        assert manager_module.cache is not None
        result = await get_cache()
        assert result is mock_instance


@pytest.mark.asyncio
async def test_shutdown_cache_on_shutdown(mock_app, mock_settings, reset_module_cache):
    """Test that the shutdown_cache event handler closes the cache correctly."""
    with patch("fastcore.cache.manager.RedisCache") as mock_redis_cache:
        # Setup mock Redis cache
        mock_instance = AsyncMock()
        mock_redis_cache.return_value = mock_instance

        # Setup cache
        setup_cache(mock_app, mock_settings)

        # Call startup event handler to initialize cache
        await mock_app.router.on_startup[0]()

        # Call shutdown event handler
        shutdown_handler = mock_app.router.on_shutdown[0]
        await shutdown_handler()

        # Verify Redis cache was closed
        mock_instance.close.assert_awaited_once()

        # Verify cache is now None
        import fastcore.cache.manager as manager_module

        assert manager_module.cache is not None  # We don't reset it to None


@pytest.mark.asyncio
async def test_setup_cache_empty_prefix(mock_app):
    """Test setup_cache with empty prefix."""
    settings = MagicMock()
    settings.CACHE_URL = "redis://localhost:6379/0"
    settings.CACHE_DEFAULT_TTL = 300
    settings.CACHE_KEY_PREFIX = None

    with patch("fastcore.cache.manager.RedisCache") as mock_redis_cache:
        # Setup mock Redis cache
        mock_instance = AsyncMock()
        mock_redis_cache.return_value = mock_instance

        # Setup cache
        setup_cache(mock_app, settings)

        # Call startup event handler
        await mock_app.router.on_startup[0]()

        # Verify Redis cache was initialized with empty prefix
        mock_redis_cache.assert_called_once_with(
            url=settings.CACHE_URL,
            default_ttl=settings.CACHE_DEFAULT_TTL,
            prefix="",
            logger=ANY,
        )
