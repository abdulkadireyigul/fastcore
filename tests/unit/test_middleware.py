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
    request = MagicMock()
    request.client.host = "1.2.3.4"
    call_next = AsyncMock(return_value="ok")
    mock_cache = AsyncMock()
    mock_cache.incr.side_effect = [1, 2]
    mock_cache.expire = AsyncMock()
    monkeypatch.setattr(
        "fastcore.middleware.rate_limiting.get_cache",
        AsyncMock(return_value=mock_cache),
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
        "fastcore.middleware.rate_limiting.get_cache",
        AsyncMock(return_value=mock_cache),
    )
    await middleware.dispatch(request, call_next)
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429
    logger.warning.assert_called()


# Route configuration test fixtures
@pytest.fixture
def complex_route_config():
    """
    Test fixture providing comprehensive route configuration scenarios.
    Includes:
    - Exact path matches
    - Pattern matches with different parameter types
    - Method-specific rate limits
    - Disabled routes
    - Nested configurations
    """
    return {
        # Exact path match with global limit
        "/api/status": {"max_requests": 1000, "window_seconds": 3600},
        # Pattern with int parameter and method-specific limits
        "/api/users/{user_id:int}": {
            "GET": {"max_requests": 100, "window_seconds": 60},
            "PUT": {"max_requests": 20, "window_seconds": 60},
            "DELETE": {"max_requests": 5, "window_seconds": 300},
        },
        # Pattern with float parameter
        "/api/items/{item_id:float}/price": {"max_requests": 50, "window_seconds": 60},
        # Pattern with path parameter and disabled rate limiting
        "/api/files/{file_path:path}": {
            "enabled": False,
            "max_requests": 10,
            "window_seconds": 60,
        },
        # Generic pattern with regex
        "/api/search/{query}": {
            "GET": {"max_requests": 30, "window_seconds": 60},
            "max_requests": 10,  # Default for other methods
            "window_seconds": 60,
        },
        # Multiple parameters
        "/api/orders/{order_id:int}/items/{item_id:int}": {
            "GET": {"max_requests": 200},
            "POST": {"max_requests": 50},
            "window_seconds": 60,  # Shared window for all methods
        },
    }


@pytest.fixture
def mock_request_factory():
    """Factory fixture to create mock requests with specific paths and methods."""

    def _make_request(path: str, method: str = "GET", client_host: str = "1.2.3.4"):
        request = MagicMock()
        request.url.path = path
        request.method = method
        request.client.host = client_host
        return request

    return _make_request


# Basic route pattern matching tests
@pytest.mark.asyncio
async def test_exact_path_rate_limit(complex_route_config, mock_request_factory):
    """Test rate limiting with exact path match configuration."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    middleware = SimpleRateLimitMiddleware(
        app=app, logger=logger, route_config=complex_route_config
    )

    request = mock_request_factory("/api/status")
    call_next = AsyncMock(return_value="ok")

    # Should allow 1000 requests per hour
    for _ in range(1000):
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"

    # The 1001st request should be blocked
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429
    logger.warning.assert_called()


@pytest.mark.asyncio
async def test_int_parameter_pattern(complex_route_config, mock_request_factory):
    """Test rate limiting with integer parameter pattern matching."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    middleware = SimpleRateLimitMiddleware(
        app=app, logger=logger, route_config=complex_route_config
    )

    # Test with valid integer parameter
    request = mock_request_factory("/api/users/123", method="GET")
    call_next = AsyncMock(return_value="ok")

    # Should allow 100 GET requests
    for _ in range(100):
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"

    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429

    # Test with invalid integer (should not match the pattern)
    request = mock_request_factory("/api/users/abc", method="GET")
    result = await middleware.dispatch(request, call_next)
    assert result == "ok"  # Should fall back to default limit


@pytest.mark.asyncio
async def test_float_parameter_pattern(complex_route_config, mock_request_factory):
    """Test rate limiting with float parameter pattern matching."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    test_config = {
        # Only include the float pattern route for focused testing
        "/api/items/{item_id:float}/price": {
            "max_requests": 5,  # Reduced for easier testing
            "window_seconds": 60,
        }
    }

    middleware = SimpleRateLimitMiddleware(
        app=app,
        logger=logger,
        route_config=test_config,
        max_requests=1000,  # High default to ensure we're hitting the pattern limit
        window_seconds=60,
    )

    # Test with valid float parameters
    valid_paths = [
        "/api/items/123.45/price",  # Standard float
        "/api/items/123.0/price",  # Integer as float
        # "/api/items/.5/price",      # Leading decimal
        # "/api/items/5./price"       # Trailing decimal
    ]

    # Configure call_next to return a proper Response object
    from fastapi import Response

    ok_response = Response(content="ok", media_type="text/plain")
    call_next = AsyncMock(return_value=ok_response)

    for path in valid_paths:
        logger.reset_mock()  # Reset logger mock for each path
        # Reset the middleware's internal state for each path
        middleware.requests = {}  # Reset memory storage

        request = mock_request_factory(path)
        request.url.path = path  # Ensure path is properly set
        request.method = "GET"  # Ensure method is set

        # Should allow exactly 5 requests per minute per the test config
        for _ in range(5):
            result = await middleware.dispatch(request, call_next)
            assert isinstance(result, Response)
            assert result.status_code == 200

        # The 6th request should be blocked due to the pattern-specific limit
        resp = await middleware.dispatch(request, call_next)
        assert isinstance(resp, Response)
        assert resp.status_code == 429
        logger.warning.assert_called_once()

        # Verify that non-matching paths fall back to the default limit
        invalid_path = "/api/items/abc/price"  # Non-float parameter
        invalid_request = mock_request_factory(invalid_path)
        result = await middleware.dispatch(invalid_request, call_next)
        assert result.status_code == 200  # Should use default limit


@pytest.mark.asyncio
async def test_method_specific_rate_limits(complex_route_config, mock_request_factory):
    """Test rate limiting with method-specific configurations."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    middleware = SimpleRateLimitMiddleware(
        app=app, logger=logger, route_config=complex_route_config
    )

    call_next = AsyncMock(return_value="ok")

    # Test GET method limit
    request = mock_request_factory("/api/users/123", method="GET")
    for _ in range(100):  # GET limit is 100
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429

    # Test PUT method limit (different limit)
    request = mock_request_factory("/api/users/123", method="PUT")
    for _ in range(20):  # PUT limit is 20
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429

    # Test DELETE method limit (longer window)
    request = mock_request_factory("/api/users/123", method="DELETE")
    for _ in range(5):  # DELETE limit is 5 with 5-minute window
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_fallback_to_default_method_limit(
    complex_route_config, mock_request_factory
):
    """Test fallback to default limit when method-specific limit is not defined."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    middleware = SimpleRateLimitMiddleware(
        app=app, logger=logger, route_config=complex_route_config
    )

    # Test with /api/search/{query} which has:
    # - GET: 30 requests per minute
    # - Others: 10 requests per minute (default)

    call_next = AsyncMock(return_value="ok")

    # Test PATCH method (should use default limit)
    request = mock_request_factory("/api/search/test-query", method="PATCH")
    for _ in range(10):  # Default limit is 10
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429

    # Test GET method (should use specific limit)
    request = mock_request_factory("/api/search/test-query", method="GET")
    for _ in range(30):  # GET limit is 30
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"
    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_disabled_route_pattern(complex_route_config, mock_request_factory):
    """Test routes with disabled rate limiting."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    middleware = SimpleRateLimitMiddleware(
        app=app, logger=logger, route_config=complex_route_config
    )

    call_next = AsyncMock(return_value="ok")

    # Test path parameter with disabled rate limiting
    request = mock_request_factory("/api/files/some/nested/path/file.txt")

    # Should allow unlimited requests since rate limiting is disabled
    for _ in range(1000):  # Test with a large number
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"

    logger.warning.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_parameters_pattern(complex_route_config, mock_request_factory):
    """Test pattern matching with multiple parameters."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    middleware = SimpleRateLimitMiddleware(
        app=app, logger=logger, route_config=complex_route_config
    )

    call_next = AsyncMock(return_value="ok")

    # Test path with multiple integer parameters
    request = mock_request_factory("/api/orders/123/items/456", method="GET")

    # Should follow GET method limit (200 requests)
    for _ in range(200):
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"

    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 429

    # Test with invalid parameters (should not match)
    invalid_paths = [
        "/api/orders/abc/items/456",  # First parameter not an int
        "/api/orders/123/items/def",  # Second parameter not an int
        "/api/orders/123.45/items/456",  # Float instead of int
    ]

    for path in invalid_paths:
        request = mock_request_factory(path, method="GET")
        result = await middleware.dispatch(request, call_next)
        assert result == "ok"  # Should use default limit


@pytest.mark.asyncio
async def test_path_parameter_pattern(complex_route_config, mock_request_factory):
    """Test pattern matching with path parameters that can contain slashes."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    middleware = SimpleRateLimitMiddleware(
        app=app, logger=logger, route_config=complex_route_config
    )

    call_next = AsyncMock(return_value="ok")

    # Test various path parameter scenarios
    test_paths = [
        "/api/files/simple.txt",
        "/api/files/nested/path/file.txt",
        "/api/files/very/deeply/nested/path/with/file.txt",
        "/api/files/path/with/special/chars/!@#$%^&*()/file.txt",
    ]

    for path in test_paths:
        request = mock_request_factory(path)
        # Should be disabled for all paths
        for _ in range(20):  # Test with more than default limit
            result = await middleware.dispatch(request, call_next)
            assert result == "ok"

        logger.warning.assert_not_called()


# Performance and Load Tests
@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test middleware behavior under concurrent load."""
    import asyncio

    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    # Configure middleware with small window for testing
    middleware = SimpleRateLimitMiddleware(
        app=app,
        logger=logger,
        max_requests=5,  # Smaller limit to ensure we hit it
        window_seconds=1,
    )

    # Configure mock response
    from fastapi import Response

    ok_response = Response(content="ok", media_type="text/plain")
    call_next = AsyncMock(return_value=ok_response)

    # Create multiple client scenarios
    clients = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]
    paths = ["/api/test1", "/api/test2", "/api/test3"]

    async def make_request(client_ip: str, path: str):
        request = MagicMock()
        request.client.host = client_ip
        request.url.path = path
        request.method = "GET"
        return await middleware.dispatch(request, call_next)

    # Test scenario 1: Single client, rapid requests
    tasks = []
    client_ip = clients[0]
    test_path = paths[0]

    # Send more requests than allowed in the window
    for _ in range(10):  # Send 10 requests when limit is 5
        tasks.append(make_request(client_ip, test_path))

    # Execute all requests concurrently
    results = await asyncio.gather(*tasks)

    # Verify results
    success_count = sum(1 for r in results if r.status_code == 200)
    blocked_count = sum(1 for r in results if r.status_code == 429)

    assert success_count == 5, "Should allow exactly max_requests successful requests"
    assert blocked_count == 5, "Should block remaining requests"
    assert success_count + blocked_count == len(tasks)

    # Test scenario 2: Multiple clients, same path
    middleware.requests = {}  # Reset middleware state
    logger.reset_mock()

    multi_client_tasks = []
    for client in clients:
        # Each client sends more than their limit
        for _ in range(7):  # 7 requests per client (limit is 5)
            multi_client_tasks.append(make_request(client, test_path))

    multi_results = await asyncio.gather(*multi_client_tasks)

    # Count results per client
    per_client_results = {}
    for i, result in enumerate(multi_results):
        client = clients[i // 7]  # Get the client for this result
        if client not in per_client_results:
            per_client_results[client] = {"success": 0, "blocked": 0}

        if result.status_code == 200:
            per_client_results[client]["success"] += 1
        else:
            per_client_results[client]["blocked"] += 1

    # Verify each client got rate limited independently
    for client, counts in per_client_results.items():
        assert (
            counts["success"] == 5
        ), f"Client {client} should get exactly 5 successful requests"
        assert counts["blocked"] == 2, f"Client {client} should have 2 requests blocked"

    assert logger.warning.call_count > 0, "Should log warnings for blocked requests"


@pytest.mark.asyncio
async def test_redis_fallback_behavior(monkeypatch):
    """Test Redis middleware fallback behavior under connection issues."""
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    middleware = RedisRateLimitMiddleware(
        app=app, logger=logger, max_requests=5, window_seconds=1
    )

    # Create a consistent request for testing
    request = MagicMock()
    request.client.host = "1.2.3.4"
    request.url.path = "/api/test"
    request.method = "GET"

    from fastapi import Response

    ok_response = Response(content="ok", media_type="text/plain")
    call_next = AsyncMock(return_value=ok_response)

    # Test scenario 1: Initial Redis connection failure
    mock_cache = AsyncMock()
    mock_cache.incr.side_effect = ConnectionError("Redis connection failed")
    mock_cache.expire = AsyncMock()

    monkeypatch.setattr(
        "fastcore.middleware.rate_limiting.get_cache",
        AsyncMock(return_value=mock_cache),
    )

    # First request should succeed and create memory fallback
    result = await middleware.dispatch(request, call_next)
    assert result.status_code == 200
    assert hasattr(middleware, "_memory_fallback"), "Should create memory fallback"
    logger.error.assert_called_once()

    # Reset mocks for clean state
    logger.reset_mock()

    # Test scenario 2: Memory fallback rate limiting
    # Should allow exactly max_requests successful requests
    for _ in range(4):  # Already used 1 request above
        result = await middleware.dispatch(request, call_next)
        assert result.status_code == 200

    # The 6th request (5 + 1 from above) should be blocked
    result = await middleware.dispatch(request, call_next)
    assert result.status_code == 429, "Should be blocked by memory fallback"

    # Reset for next scenario
    middleware._memory_fallback.requests = {}
    logger.reset_mock()

    # Test scenario 3: Redis recovery
    mock_cache.incr.side_effect = None  # Redis is back
    mock_cache.incr.return_value = 1  # First request in new window

    # Should succeed and use Redis again
    result = await middleware.dispatch(request, call_next)
    assert result.status_code == 200
    mock_cache.expire.assert_awaited_once()
    logger.error.assert_not_called()

    # Test scenario 4: Redis fails again
    mock_cache.reset_mock()
    mock_cache.incr.side_effect = ConnectionError("Redis failed again")
    logger.reset_mock()

    # Should reuse existing memory fallback
    prev_fallback = middleware._memory_fallback
    result = await middleware.dispatch(request, call_next)
    assert (
        middleware._memory_fallback is prev_fallback
    ), "Should reuse existing fallback"
    assert result.status_code == 200
    logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_memory_usage():
    """Test middleware memory usage under extended operation."""
    import asyncio
    import gc
    import os
    import time

    try:
        import psutil
    except ImportError:
        pytest.skip("psutil package is required for memory usage tests")

    process = psutil.Process(os.getpid())

    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    # Configure middleware with shorter window for testing
    middleware = SimpleRateLimitMiddleware(
        app=app, logger=logger, max_requests=1000, window_seconds=2
    )

    # Reset logger mock after middleware initialization
    logger.reset_mock()

    from fastapi import Response

    ok_response = Response(content="ok", media_type="text/plain")
    call_next = AsyncMock(return_value=ok_response)

    # Record initial memory usage
    gc.collect()  # Force garbage collection
    initial_memory = process.memory_info().rss

    # Simulate heavy usage over multiple time windows, but with smaller load
    start_time = time.time()
    request_count = 0
    unique_ips = [f"192.168.1.{i}" for i in range(10)]  # Reduced from 100 to 10 IPs
    paths = [f"/api/test{i}" for i in range(3)]  # Reduced from 10 to 3 paths

    # Create request object once and reuse it to reduce object creation
    request = MagicMock()
    request.method = "GET"

    while time.time() - start_time < 3:  # Run for 3 seconds
        for ip in unique_ips:
            for path in paths:
                request.client.host = ip
                request.url.path = path
                await middleware.dispatch(request, call_next)
                request_count += 1

        # Force window rotation every second
        await asyncio.sleep(1)

    # Record final memory usage
    gc.collect()  # Force garbage collection
    final_memory = process.memory_info().rss

    # Calculate memory growth
    memory_growth = final_memory - initial_memory
    memory_growth_mb = memory_growth / (1024 * 1024)  # Convert to MB

    # Log performance metrics
    logger.info.assert_not_called()  # Should not have any unexpected logs
    print(f"\nPerformance Test Results:")
    print(f"Total requests processed: {request_count}")
    print(f"Memory growth: {memory_growth_mb:.2f} MB")
    print(f"Memory per request: {(memory_growth / request_count):.2f} bytes")

    # Assert reasonable memory usage
    # Given the test framework overhead and necessary object creation,
    # allow up to 50MB growth for the test duration
    assert (
        memory_growth_mb < 50
    ), f"Memory growth ({memory_growth_mb:.2f}MB) exceeds threshold"

    # Verify rate limiting behavior across windows
    initial_window = int(time.time()) // middleware.window_seconds
    initial_key = (
        f"{request.client.host}:{request.method}:{request.url.path}:{initial_window}"
    )
    assert initial_key in middleware.requests, "Current window key should exist"

    # Wait for window to expire
    await asyncio.sleep(3)  # Window is 2 seconds

    # Make request in new window
    await middleware.dispatch(request, call_next)

    # Get current window
    current_window = int(time.time()) // middleware.window_seconds
    current_key = (
        f"{request.client.host}:{request.method}:{request.url.path}:{current_window}"
    )

    # Verify the keys are for different windows
    assert initial_window != current_window, "Windows should be different"
    assert middleware.requests[current_key] == 1, "New window should start count at 1"
