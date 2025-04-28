"""
Unit tests for the middleware module.

Covers:
- CORS middleware configuration and logging
- Middleware manager setup and delegation
- Rate limiting middleware (memory and Redis backends)
- All logging, configuration, and error branches

All tests use mocks to isolate FastAPI app, logger, and cache dependencies.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from src.middleware.cors import add_cors_middleware
from src.middleware.manager import setup_middlewares
from src.middleware.rate_limiting import (
    RedisRateLimitMiddleware,
    SimpleRateLimitMiddleware,
    add_rate_limiting_middleware,
)


# --- cors.py ---
def test_add_cors_middleware_defaults():
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    logger = MagicMock()
    del settings.MIDDLEWARE_CORS_OPTIONS
    add_cors_middleware(app, settings, logger)
    app.add_middleware.assert_called()
    logger.info.assert_called()
    logger.debug.assert_called()


def test_add_cors_middleware_custom():
    from fastapi.middleware.cors import CORSMiddleware

    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    logger = MagicMock()
    settings.MIDDLEWARE_CORS_OPTIONS = {
        "allow_origins": ["https://foo"],
        "allow_methods": ["GET"],
    }
    add_cors_middleware(app, settings, logger)
    app.add_middleware.assert_called_with(
        CORSMiddleware, allow_origins=["https://foo"], allow_methods=["GET"]
    )
    logger.info.assert_called()
    logger.debug.assert_called()


# --- manager.py ---
def test_setup_middlewares(monkeypatch):
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    logger = MagicMock()
    called = {}
    monkeypatch.setattr(
        "src.middleware.manager.add_cors_middleware",
        lambda *a, **kw: called.setdefault("cors", True),
    )
    monkeypatch.setattr(
        "src.middleware.manager.add_rate_limiting_middleware",
        lambda *a, **kw: called.setdefault("rate", True),
    )
    setup_middlewares(app, settings, logger)
    assert called["cors"]
    assert called["rate"]


# --- rate_limiting.py ---
def test_add_rate_limiting_middleware_memory():
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    logger = MagicMock()
    settings.RATE_LIMITING_BACKEND = "memory"
    settings.RATE_LIMITING_OPTIONS = {"max_requests": 2, "window_seconds": 60}
    add_rate_limiting_middleware(app, settings, logger)
    app.add_middleware.assert_called_with(
        SimpleRateLimitMiddleware, logger=logger, max_requests=2, window_seconds=60
    )
    logger.info.assert_called()
    logger.debug.assert_called()


def test_add_rate_limiting_middleware_redis():
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    logger = MagicMock()
    settings.RATE_LIMITING_BACKEND = "redis"
    settings.RATE_LIMITING_OPTIONS = {"max_requests": 2, "window_seconds": 60}
    add_rate_limiting_middleware(app, settings, logger)
    app.add_middleware.assert_called_with(
        RedisRateLimitMiddleware, logger=logger, max_requests=2, window_seconds=60
    )
    logger.info.assert_called()
    logger.debug.assert_called()


@pytest.mark.asyncio
async def test_simple_rate_limit_middleware_allows():
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=2, window_seconds=60, logger=logger
    )
    request = MagicMock()
    request.client.host = "1.2.3.4"
    call_next = AsyncMock(return_value="ok")
    result = await middleware.dispatch(request, call_next)
    assert result == "ok"
    result = await middleware.dispatch(request, call_next)
    assert result == "ok"


@pytest.mark.asyncio
async def test_simple_rate_limit_middleware_blocks():
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=1, window_seconds=60, logger=logger
    )
    request = MagicMock()
    request.client.host = "1.2.3.4"
    call_next = AsyncMock(return_value="ok")
    await middleware.dispatch(request, call_next)
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429
    logger.warning.assert_called()


@pytest.mark.asyncio
async def test_redis_rate_limit_middleware_allows(monkeypatch):
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()
    middleware = RedisRateLimitMiddleware(
        app, max_requests=2, window_seconds=60, logger=logger
    )
    request = MagicMock()
    request.client.host = "1.2.3.4"
    call_next = AsyncMock(return_value="ok")
    mock_cache = AsyncMock()
    mock_cache.incr.side_effect = [1, 2]
    mock_cache.expire = AsyncMock()
    monkeypatch.setattr(
        "src.middleware.rate_limiting.get_cache", AsyncMock(return_value=mock_cache)
    )
    result = await middleware.dispatch(request, call_next)
    assert result == "ok"
    result = await middleware.dispatch(request, call_next)
    assert result == "ok"
    mock_cache.expire.assert_awaited()


@pytest.mark.asyncio
async def test_redis_rate_limit_middleware_blocks(monkeypatch):
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()
    middleware = RedisRateLimitMiddleware(
        app, max_requests=1, window_seconds=60, logger=logger
    )
    request = MagicMock()
    request.client.host = "1.2.3.4"
    call_next = AsyncMock(return_value="ok")
    mock_cache = AsyncMock()
    mock_cache.incr.side_effect = [1, 2]
    mock_cache.expire = AsyncMock()
    monkeypatch.setattr(
        "src.middleware.rate_limiting.get_cache", AsyncMock(return_value=mock_cache)
    )
    await middleware.dispatch(request, call_next)
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429
    logger.warning.assert_called()
