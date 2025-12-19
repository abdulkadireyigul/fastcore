"""
Unit tests for the middleware module.

Covers:
- CORS middleware configuration and logging
- Middleware manager setup and delegation
- Rate limiting middleware (memory and Redis backends)
- All logging, configuration, and error branches

All tests use mocks to isolate FastAPI app, logger, and cache dependencies.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from fastcore.config.base import BaseAppSettings
from fastcore.middleware.cors import add_cors_middleware
from fastcore.middleware.manager import setup_middlewares
from fastcore.middleware.rate_limiting import (
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
        "fastcore.middleware.manager.add_cors_middleware",
        lambda *a, **kw: called.setdefault("cors", True),
    )
    monkeypatch.setattr(
        "fastcore.middleware.manager.add_rate_limiting_middleware",
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
    import sys

    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    logger = MagicMock()
    settings.RATE_LIMITING_BACKEND = "redis"
    settings.RATE_LIMITING_OPTIONS = {"max_requests": 2, "window_seconds": 60}
    # sys.modules üzerinden cache'i mockla
    manager_mod = sys.modules["fastcore.cache.manager"]
    manager_mod.cache = MagicMock()
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
    # request = MagicMock()
    # request.client.host = "1.2.3.4"
    # call_next = AsyncMock(return_value="ok")
    # mock_cache = AsyncMock()
    # mock_cache.incr.side_effect = [1, 2]
    # mock_cache.expire = AsyncMock()
    # monkeypatch.setattr(
    #     "fastcore.middleware.rate_limiting.get_cache",
    #     AsyncMock(return_value=mock_cache),
    # )
    # result = await middleware.dispatch(request, call_next)
    # assert result == "ok"
    # result = await middleware.dispatch(request, call_next)
    # assert result == "ok"
    # mock_cache.expire.assert_awaited()

    mock_cache = AsyncMock()
    mock_cache.incr_with_expire = AsyncMock(side_effect=[1, 2])

    monkeypatch.setattr(
        "fastcore.middleware.rate_limiting.get_cache",
        AsyncMock(return_value=mock_cache),
    )

    request = MagicMock()
    request.client.host = "1.2.3.4"
    request.method = "GET"
    request.url.path = "/test"

    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    response_1 = await middleware.dispatch(request, call_next)
    assert response_1.status_code == 200
    assert response_1.headers["X-RateLimit-Remaining"] == "1"

    response_2 = await middleware.dispatch(request, call_next)
    assert response_2.status_code == 200
    assert response_2.headers["X-RateLimit-Remaining"] == "0"

    mock_cache.incr_with_expire.assert_called()


@pytest.mark.asyncio
async def test_redis_rate_limit_middleware_blocks(monkeypatch):
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()
    middleware = RedisRateLimitMiddleware(
        app, max_requests=1, window_seconds=60, logger=logger
    )
    # request = MagicMock()
    # request.client.host = "1.2.3.4"
    # call_next = AsyncMock(return_value="ok")
    # mock_cache = AsyncMock()
    # mock_cache.incr.side_effect = [1, 2]
    # mock_cache.expire = AsyncMock()
    # monkeypatch.setattr(
    #     "fastcore.middleware.rate_limiting.get_cache",
    #     AsyncMock(return_value=mock_cache),
    # )
    # await middleware.dispatch(request, call_next)
    # resp = await middleware.dispatch(request, call_next)
    # assert resp.status_code == 429
    # logger.warning.assert_called()

    mock_cache = AsyncMock()
    mock_cache.incr_with_expire = AsyncMock(side_effect=[1, 2])

    monkeypatch.setattr(
        "fastcore.middleware.rate_limiting.get_cache",
        AsyncMock(return_value=mock_cache),
    )

    request = MagicMock()
    request.client.host = "1.2.3.4"
    request.method = "GET"
    request.url.path = "/test"
    call_next = AsyncMock(return_value=Response(content="ok", status_code=200))

    await middleware.dispatch(request, call_next)

    resp = await middleware.dispatch(request, call_next)

    assert resp.status_code == 429
    logger.warning.assert_called()
    assert "X-RateLimit-Limit" in resp.headers


from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request
from starlette.responses import Response

# # from your_module import (  # Adjust import path
# #     SimpleRateLimitMiddleware,
# #     RedisRateLimitMiddleware,
# #     add_rate_limiting_middleware
# # )


# class MockSettings(BaseModel):
#     """Mock settings class for testing"""

#     def __init__(self, rate_limiting_options=None, rate_limiting_backend="memory"):
#         self.RATE_LIMITING_OPTIONS = rate_limiting_options or {
#             "max_requests": 60,
#             "window_seconds": 60,
#         }
#         self.RATE_LIMITING_BACKEND = rate_limiting_backend


@pytest.fixture
def mock_logger():
    """Mock logger fixture"""
    logger = Mock()
    logger.info = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def app():
    """FastAPI app fixture"""
    return FastAPI()


@pytest.fixture
def mock_request():
    """Mock request fixture"""
    request = Mock(spec=Request)
    request.client.host = "192.168.1.1"
    request.method = "GET"
    request.url.path = "/api/test"
    return request


# Test base middleware functionality
def test_fastapi_to_regex_simple_path(app, mock_logger):
    """Test regex conversion for simple paths"""
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger)
    result = middleware._fastapi_to_regex("/api/users")
    assert result == "^/api/users/?$"


def test_fastapi_to_regex_with_params(app, mock_logger):
    """Test regex conversion with path parameters"""
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger)

    # Test string parameter
    result = middleware._fastapi_to_regex("/api/users/{user_id}")
    assert result == "^/api/users/([^/]+)/?$"

    # Test int parameter
    result = middleware._fastapi_to_regex("/api/users/{user_id:int}")
    assert result == "^/api/users/(\\d+)/?$"

    # Test float parameter
    result = middleware._fastapi_to_regex("/api/users/{price:float}")
    assert result == "^/api/users/([\\d\\.]+)/?$"


def test_fastapi_to_regex_complex_path(app, mock_logger):
    """Test regex conversion for complex DZI path"""
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger)
    result = middleware._fastapi_to_regex(
        "/dzi/{slide_id}_files/{level:int}/{col:int}_{row:int}.jpeg"
    )
    expected = "^/dzi/([^/]+)_files/(\\d+)/(\\d+)_(\\d+)\\.jpeg/?$"
    assert result == expected


# Test route configuration matching logic
def test_exact_path_match(app, mock_logger):
    """Test exact path matching"""
    routes = {"/api/users": {"max_requests": 10, "window_seconds": 60}}
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger, routes=routes)

    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "GET", "/api/users"
    )
    assert max_req == 10
    assert window == 60
    assert disabled == False


def test_method_specific_match(app, mock_logger):
    """Test method-specific path matching"""
    routes = {
        "POST:/api/users": {"max_requests": 5, "window_seconds": 300},
        "GET:/api/users": {"max_requests": 100, "window_seconds": 60},
    }
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger, routes=routes)

    # Test POST
    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "POST", "/api/users"
    )
    assert max_req == 5
    assert window == 300

    # Test GET
    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "GET", "/api/users"
    )
    assert max_req == 100
    assert window == 60


def test_method_priority_over_general(app, mock_logger):
    """Test that method-specific config has priority over general"""
    routes = {
        "/api/users": {"max_requests": 50, "window_seconds": 60},
        "POST:/api/users": {"max_requests": 5, "window_seconds": 300},
    }
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger, routes=routes)

    # POST should use method-specific config
    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "POST", "/api/users"
    )
    assert max_req == 5
    assert window == 300

    # GET should use general config
    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "GET", "/api/users"
    )
    assert max_req == 50
    assert window == 60


def test_regex_pattern_matching(app, mock_logger):
    """Test regex pattern matching for dynamic routes"""
    routes = {"/api/users/{user_id:int}": {"max_requests": 20, "window_seconds": 60}}
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger, routes=routes)

    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "GET", "/api/users/123"
    )
    assert max_req == 20
    assert window == 60


def test_method_regex_pattern_matching(app, mock_logger):
    """Test method-specific regex pattern matching"""
    routes = {
        "GET:/dzi/{slide_id}_files/{level:int}/{col:int}_{row:int}.jpeg": {
            "max_requests": 1000,
            "window_seconds": 60,
        }
    }
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger, routes=routes)

    # Should match GET request
    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "GET", "/dzi/slide123_files/5/10_20.jpeg"
    )
    assert max_req == 1000
    assert window == 60

    # Should not match POST request (use defaults)
    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "POST", "/dzi/slide123_files/5/10_20.jpeg"
    )
    assert max_req == 60  # default
    assert window == 60  # default


def test_disabled_route(app, mock_logger):
    """Test disabled route configuration"""
    routes = {"/api/no-limit": {"disabled": True}}
    middleware = SimpleRateLimitMiddleware(app, logger=mock_logger, routes=routes)

    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "GET", "/api/no-limit"
    )
    assert disabled == True


def test_default_config_fallback(app, mock_logger):
    """Test fallback to default config when no route matches"""
    routes = {"/api/users": {"max_requests": 10, "window_seconds": 60}}
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=100, window_seconds=120, logger=mock_logger, routes=routes
    )

    # Non-matching route should use defaults
    matched_pattern, max_req, window, disabled = middleware._get_route_config(
        "GET", "/api/other"
    )
    assert max_req == 100
    assert window == 120
    assert disabled == False


# Test SimpleRateLimitMiddleware functionality
@pytest.mark.asyncio
async def test_rate_limiting_basic(app, mock_logger):
    """Test basic rate limiting functionality"""
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=2, window_seconds=60, logger=mock_logger
    )

    request = Mock(spec=Request)
    request.client.host = "192.168.1.1"
    request.method = "GET"
    request.url.path = "/api/test"

    call_next = AsyncMock(return_value=Response("OK"))

    # First two requests should pass
    response1 = await middleware.dispatch(request, call_next)
    response2 = await middleware.dispatch(request, call_next)

    assert call_next.call_count == 2

    # Third request should be rate limited
    response3 = await middleware.dispatch(request, call_next)
    assert response3.status_code == 429
    assert response3.body.decode() == "Too Many Requests"


@pytest.mark.asyncio
async def test_disabled_route_bypass(app, mock_logger):
    """Test that disabled routes bypass rate limiting"""
    routes = {"/api/no-limit": {"disabled": True}}
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=1, window_seconds=60, logger=mock_logger, routes=routes
    )

    request = Mock(spec=Request)
    request.client.host = "192.168.1.1"
    request.method = "GET"
    request.url.path = "/api/no-limit"

    call_next = AsyncMock(return_value=Response("OK"))

    # Multiple requests should all pass
    for _ in range(5):
        response = await middleware.dispatch(request, call_next)
        assert response.body.decode() == "OK"

    assert call_next.call_count == 5


@pytest.mark.asyncio
async def test_different_ips_separate_limits(app, mock_logger):
    """Test that different IPs have separate rate limits"""
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=1, window_seconds=60, logger=mock_logger
    )

    request1 = Mock(spec=Request)
    request1.client.host = "192.168.1.1"
    request1.method = "GET"
    request1.url.path = "/api/test"

    request2 = Mock(spec=Request)
    request2.client.host = "192.168.1.2"
    request2.method = "GET"
    request2.url.path = "/api/test"

    call_next = AsyncMock(return_value=Response("OK"))

    # Both IPs should be able to make one request
    response1 = await middleware.dispatch(request1, call_next)
    response2 = await middleware.dispatch(request2, call_next)

    assert call_next.call_count == 2


@pytest.mark.asyncio
async def test_different_methods_separate_limits(app, mock_logger):
    """Test that different methods have separate rate limits"""
    routes = {
        "GET:/api/test": {"max_requests": 1, "window_seconds": 60},
        "POST:/api/test": {"max_requests": 2, "window_seconds": 60},
    }
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=10, window_seconds=60, logger=mock_logger, routes=routes
    )

    get_request = Mock(spec=Request)
    get_request.client.host = "192.168.1.1"
    get_request.method = "GET"
    get_request.url.path = "/api/test"

    post_request = Mock(spec=Request)
    post_request.client.host = "192.168.1.1"
    post_request.method = "POST"
    post_request.url.path = "/api/test"

    call_next = AsyncMock(return_value=Response("OK"))

    # GET: 1 request should pass, 2nd should fail
    await middleware.dispatch(get_request, call_next)
    response = await middleware.dispatch(get_request, call_next)
    assert response.status_code == 429

    # POST: 2 requests should pass
    await middleware.dispatch(post_request, call_next)
    response = await middleware.dispatch(post_request, call_next)
    assert response.body.decode() == "OK"


@pytest.mark.asyncio
async def test_different_paths_separate_limits(app, mock_logger):
    """Test that different paths have separate rate limits"""
    routes = {
        "/api/heavy": {"max_requests": 1, "window_seconds": 60},
        "/api/light": {"max_requests": 5, "window_seconds": 60},
    }
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=10, window_seconds=60, logger=mock_logger, routes=routes
    )

    heavy_request = Mock(spec=Request)
    heavy_request.client.host = "192.168.1.1"
    heavy_request.method = "GET"
    heavy_request.url.path = "/api/heavy"

    light_request = Mock(spec=Request)
    light_request.client.host = "192.168.1.1"
    light_request.method = "GET"
    light_request.url.path = "/api/light"

    call_next = AsyncMock(return_value=Response("OK"))

    # Heavy endpoint: 1 request should pass, 2nd should fail
    await middleware.dispatch(heavy_request, call_next)
    response = await middleware.dispatch(heavy_request, call_next)
    assert response.status_code == 429

    # Light endpoint: should still work (separate counter)
    response = await middleware.dispatch(light_request, call_next)
    assert response.body.decode() == "OK"


@pytest.mark.asyncio
async def test_dynamic_route_matching(app, mock_logger):
    """Test dynamic route matching with real path"""
    routes = {
        "/dzi/{slide_id}_files/{level:int}/{col:int}_{row:int}.jpeg": {
            "max_requests": 2,
            "window_seconds": 60,
        }
    }
    middleware = SimpleRateLimitMiddleware(
        app, max_requests=1, window_seconds=60, logger=mock_logger, routes=routes
    )

    request = Mock(spec=Request)
    request.client.host = "192.168.1.1"
    request.method = "GET"
    request.url.path = "/dzi/slide123_files/5/10_20.jpeg"

    call_next = AsyncMock(return_value=Response("OK"))

    # Should use route-specific config (2 requests allowed)
    await middleware.dispatch(request, call_next)
    await middleware.dispatch(request, call_next)
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429


# Test Redis middleware functionality
@pytest.mark.asyncio
async def test_redis_rate_limiting_success(app, mock_logger):
    """Test Redis-based rate limiting when cache works"""
    mock_cache = AsyncMock()
    # mock_cache.incr.return_value = 1
    mock_cache.incr_with_expire = AsyncMock(return_value=1)
    # mock_cache.expire = AsyncMock()

    with patch(
        "fastcore.middleware.rate_limiting.get_cache", return_value=mock_cache
    ):  # Adjust import
        middleware = RedisRateLimitMiddleware(
            app, max_requests=2, window_seconds=60, logger=mock_logger
        )

        request = Mock(spec=Request)
        request.client.host = "192.168.1.1"
        request.method = "GET"
        request.url.path = "/api/test"

        # call_next = AsyncMock(return_value=Response("OK"))
        call_next = AsyncMock(return_value=Response("OK", status_code=200))

        response = await middleware.dispatch(request, call_next)

        # assert call_next.call_count == 1
        # mock_cache.incr.assert_called_once()
        # mock_cache.expire.assert_called_once()

        assert response.status_code == 200
        assert call_next.call_count == 1

        mock_cache.incr_with_expire.assert_called_once()
        assert "X-RateLimit-Limit" in response.headers


@pytest.mark.asyncio
async def test_redis_rate_limiting_fallback_to_memory(app, mock_logger):
    """Test Redis middleware falls back to memory when cache fails"""
    with patch(
        "fastcore.middleware.rate_limiting.get_cache",
        side_effect=Exception("Redis down"),
    ):  # Adjust import
        middleware = RedisRateLimitMiddleware(
            app, max_requests=1, window_seconds=60, logger=mock_logger
        )

        request = Mock(spec=Request)
        request.client.host = "192.168.1.1"
        request.method = "GET"
        request.url.path = "/api/test"

        call_next = AsyncMock(return_value=Response("OK"))

        # First request should work (fallback to memory)
        response1 = await middleware.dispatch(request, call_next)
        assert call_next.call_count == 1

        # Second request should be rate limited (memory backend working)
        response2 = await middleware.dispatch(request, call_next)
        assert response2.status_code == 429

        # Check error was logged
        mock_logger.error.assert_called()


# Test middleware setup function
def test_add_rate_limiting_middleware_memory_backend(mock_logger):
    """Test middleware setup with memory backend"""
    app = FastAPI()
    settings = MagicMock()
    settings.rate_limiting_options = {"max_requests": 100, "window_seconds": 60}
    settings.rate_limiting_backend = "memory"

    add_rate_limiting_middleware(app, settings, mock_logger)

    # Check middleware was added
    assert len(app.user_middleware) == 1
    mock_logger.info.assert_called()
    mock_logger.debug.assert_called()


def test_add_rate_limiting_middleware_redis_backend(mock_logger):
    """Test middleware setup with Redis backend"""
    app = FastAPI()
    settings = MagicMock()
    settings.rate_limiting_options = {"max_requests": 50, "window_seconds": 30}
    settings.rate_limiting_backend = "redis"

    add_rate_limiting_middleware(app, settings, mock_logger)

    # Check middleware was added
    assert len(app.user_middleware) == 1
    mock_logger.info.assert_called()
    mock_logger.debug.assert_called()


# def test_add_rate_limiting_middleware_with_routes(mock_logger):
#     """Test middleware setup with route-specific configs"""
#     app = FastAPI()
#     settings = MagicMock()
#     settings.rate_limiting_options = {
#         "max_requests": 60,
#         "window_seconds": 60,
#         "routes": {
#             "/api/heavy": {"max_requests": 10, "window_seconds": 60},
#             "POST:/api/users": {"max_requests": 5, "window_seconds": 300},
#         },
#     }
#     settings.rate_limiting_backend = "memory"

#     add_rate_limiting_middleware(app, settings, mock_logger)

#     # Check middleware was added
#     assert len(app.user_middleware) == 1

#     # Verify log message mentions route configs
#     call_args = mock_logger.info.call_args[0][0]
#     # assert "routes={'/api/heavy'" in call_args
#     assert "backend=memory" in call_args
#     assert "options=" in call_args


def test_add_rate_limiting_middleware_default_settings(mock_logger):
    """Test middleware setup with default settings"""
    app = FastAPI()
    settings = MagicMock()

    add_rate_limiting_middleware(app, settings, mock_logger)

    # Check middleware was added with defaults
    assert len(app.user_middleware) == 1
    mock_logger.info.assert_called()
    mock_logger.debug.assert_called()


# Integration-style tests
@pytest.mark.asyncio
async def test_end_to_end_rate_limiting_scenario(app, mock_logger):
    """Test a realistic end-to-end scenario"""
    routes = {
        # API endpoints with different limits
        "POST:/api/login": {
            "max_requests": 3,
            "window_seconds": 300,
        },  # Strict login rate limit
        "GET:/api/users": {
            "max_requests": 100,
            "window_seconds": 60,
        },  # Generous read limit
        "/api/heavy-compute": {
            "max_requests": 2,
            "window_seconds": 60,
        },  # Any method, low limit
        # File serving with high limits
        "GET:/dzi/{slide_id}_files/{level:int}/{col:int}_{row:int}.jpeg": {
            "max_requests": 1000,
            "window_seconds": 60,
        },
        # Unlimited endpoint
        "/health": {"disabled": True},
    }

    middleware = SimpleRateLimitMiddleware(
        app, max_requests=50, window_seconds=60, logger=mock_logger, routes=routes
    )

    call_next = AsyncMock(return_value=Response("OK"))

    # Test login rate limiting (strict)
    login_request = Mock(spec=Request)
    login_request.client.host = "192.168.1.1"
    login_request.method = "POST"
    login_request.url.path = "/api/login"

    for i in range(3):
        response = await middleware.dispatch(login_request, call_next)
        assert response.body.decode() == "OK"

    # 4th login should fail
    response = await middleware.dispatch(login_request, call_next)
    assert response.status_code == 429

    # Test health check (unlimited)
    health_request = Mock(spec=Request)
    health_request.client.host = "192.168.1.1"
    health_request.method = "GET"
    health_request.url.path = "/health"

    # Should work unlimited times
    for _ in range(10):
        response = await middleware.dispatch(health_request, call_next)
        assert response.body.decode() == "OK"

    # Test DZI file serving (high limit, different IP)
    dzi_request = Mock(spec=Request)
    dzi_request.client.host = "192.168.1.2"  # Different IP
    dzi_request.method = "GET"
    dzi_request.url.path = "/dzi/slide123_files/5/10_20.jpeg"

    # Should handle many requests
    for _ in range(100):
        response = await middleware.dispatch(dzi_request, call_next)
        assert response.body.decode() == "OK"


@pytest.fixture
def mock_bench_app():
    """Creates a mock FastAPI application for testing."""
    app = FastAPI()

    @app.get("/users/{user_id}")
    async def read_user(user_id: int):
        return {"user_id": user_id}

    return app


@pytest.fixture
def rate_limit_middleware(mock_bench_app):
    """Creates a SimpleRateLimitMiddleware instance with route-based configuration."""
    return SimpleRateLimitMiddleware(
        mock_bench_app,
        max_requests=10000,
        window_seconds=60,
        logger=MagicMock(),
        routes={
            "GET:/users/{user_id}": {"max_requests": 1000, "window_seconds": 60},
        },
    )


@pytest.fixture
def redis_rate_limit_middleware(mock_app, mock_redis_cache):
    """
    Creates a RedisRateLimitMiddleware instance for benchmarking.
    """
    return RedisRateLimitMiddleware(
        mock_app,
        max_requests=10000,
        window_seconds=60,
        logger=MagicMock(),
        routes={"GET:/users/{user_id}": {"max_requests": 1000, "window_seconds": 60}},
    )


def test_benchmark_route_config_lookup(benchmark, rate_limit_middleware):
    """
    Tests the performance of the cached route configuration lookup.
    The first call measures a cache miss, while subsequent calls measure a cache hit.
    """

    # The benchmark fixture should be used only once per function.
    # We will measure the performance of a sequence of calls within the benchmarked function.

    def run_lookups():
        # First call: cache miss
        rate_limit_middleware._get_route_config("GET", "/users/123")

        # Subsequent calls: cache hit
        rate_limit_middleware._get_route_config("GET", "/users/123")
        rate_limit_middleware._get_route_config("GET", "/users/456")

        # Another cache miss on a completely new path
        rate_limit_middleware._get_route_config("GET", "/new-path/789")

    benchmark(run_lookups)


def test_benchmark_dispatch_performance(
    benchmark, mock_bench_app, rate_limit_middleware
):
    """
    Tests the end-to-end performance of the middleware's dispatch method.
    Fixed: Uses a sync wrapper to ensure the async code is actually executed.
    """
    request = MagicMock()
    request.method = "GET"
    request.client.host = "127.0.0.1"
    request.url.path = "/users/123"

    # We need a simple async function to mock call_next
    async def mock_call_next(req):
        return Response(status_code=200)

    def sync_wrapper():
        asyncio.run(rate_limit_middleware.dispatch(request, mock_call_next))

    benchmark(sync_wrapper)


@pytest.fixture
def redis_rate_limit_middleware(mock_bench_app):
    """
    Creates a RedisRateLimitMiddleware instance for benchmarking.
    """
    return RedisRateLimitMiddleware(
        mock_bench_app,
        max_requests=10000,
        window_seconds=60,
        logger=MagicMock(),
        routes={"GET:/users/{user_id}": {"max_requests": 1000, "window_seconds": 60}},
    )


def test_benchmark_redis_dispatch_performance(benchmark, redis_rate_limit_middleware):
    """
    Benchmarks the end-to-end performance of the Redis rate-limiting middleware.
    Fixed: Uses a sync wrapper to ensure the async code is actually executed.
    """
    request = MagicMock()
    request.method = "GET"
    request.client.host = "127.0.0.1"
    request.url.path = "/users/123"

    async def mock_call_next(req):
        return Response(status_code=200)

    def sync_wrapper():
        asyncio.run(redis_rate_limit_middleware.dispatch(request, mock_call_next))

    benchmark(sync_wrapper)
