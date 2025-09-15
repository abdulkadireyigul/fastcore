"""
Test module for comprehensive route configuration testing in rate limiting middleware.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Response

from fastcore.middleware.rate_limiting import SimpleRateLimitMiddleware


@pytest.mark.asyncio
async def test_route_config_comprehensive():
    """
    Comprehensive test of rate limiting behavior with route_config.
    Tests default behavior, disabled routes, custom limits, and pattern matching.
    """
    app = MagicMock(spec=FastAPI)
    logger = MagicMock()

    # Test Setup: Configure middleware with various route configurations
    route_config = {
        # 1. Explicitly disabled route
        "/api/public/status": {
            "enabled": False  # This route should never be rate limited
        },
        # 2. Route with custom limits
        "/api/users": {"max_requests": 3, "window_seconds": 1},  # Stricter than default
        # 3. Pattern matching for dynamic routes
        "/api/products/{product_id:int}": {"max_requests": 10, "window_seconds": 1},
        # 4. Route with method-specific limits
        "/api/orders": {
            "GET": {"max_requests": 20},
            "POST": {"max_requests": 5},
            "window_seconds": 1,
        },
    }

    # Create middleware with default limits (5 requests per second)
    middleware = SimpleRateLimitMiddleware(
        app=app,
        logger=logger,
        max_requests=5,  # Default global limit
        window_seconds=1,
        route_config=route_config,
    )

    # Configure common test components
    ok_response = Response(content="ok", media_type="text/plain")
    call_next = AsyncMock(return_value=ok_response)

    async def make_requests(path: str, method: str, count: int) -> list:
        """Helper function to make multiple requests and return their status codes"""
        results = []
        request = MagicMock()
        request.client.host = "test.ip"
        request.url.path = path
        request.method = method

        for _ in range(count):
            response = await middleware.dispatch(request, call_next)
            results.append(response.status_code)
        return results

    # Test 1: Disabled route should never be rate limited
    print("\nTesting disabled route...")
    results = await make_requests("/api/public/status", "GET", 20)
    assert all(
        code == 200 for code in results
    ), "Disabled route should never be rate limited"

    # Reset middleware state
    middleware.requests = {}

    # Test 2: Custom rate limited route
    print("\nTesting custom rate limited route...")
    results = await make_requests("/api/users", "GET", 5)
    assert results[:3] == [200, 200, 200], "First 3 requests should succeed"
    assert results[3:] == [429, 429], "Requests after limit should be blocked"

    # Reset middleware state
    middleware.requests = {}

    # Test 3: Pattern matching with dynamic route
    print("\nTesting pattern matching...")
    # Test with valid integer parameter
    results = await make_requests("/api/products/123", "GET", 12)
    assert all(code == 200 for code in results[:10]), "First 10 requests should succeed"
    assert all(
        code == 429 for code in results[10:]
    ), "Requests after 10 should be blocked"

    # Reset middleware state
    middleware.requests = {}

    # Test with invalid parameter (should use default limit)
    results = await make_requests("/api/products/abc", "GET", 7)
    assert all(code == 200 for code in results[:5]), "Should use default limit (5)"
    assert all(code == 429 for code in results[5:]), "Should be blocked after 5"

    # Reset middleware state
    middleware.requests = {}

    # Test 4: Method-specific limits
    print("\nTesting method-specific limits...")
    # GET requests (limit 20)
    results = await make_requests("/api/orders", "GET", 22)
    assert all(
        code == 200 for code in results[:20]
    ), "First 20 GET requests should succeed"
    assert all(
        code == 429 for code in results[20:]
    ), "GET requests after 20 should be blocked"

    # Reset middleware state
    middleware.requests = {}

    # POST requests (limit 5)
    results = await make_requests("/api/orders", "POST", 7)
    assert all(
        code == 200 for code in results[:5]
    ), "First 5 POST requests should succeed"
    assert all(
        code == 429 for code in results[5:]
    ), "POST requests after 5 should be blocked"

    # Reset middleware state
    middleware.requests = {}

    # Test 5: Unconfigured route (should use default limits)
    print("\nTesting unconfigured route...")
    results = await make_requests("/api/unconfigured", "GET", 7)
    assert all(code == 200 for code in results[:5]), "Should use default limit"
    assert all(
        code == 429 for code in results[5:]
    ), "Should be blocked after default limit"

    # Test 6: Verify warning logs
    assert logger.warning.called, "Should log warnings for rate limit violations"

    # Print summary
    print("\nAll tests passed successfully!")
    print("✓ Disabled routes remain unrestricted")
    print("✓ Custom rate limits are enforced")
    print("✓ Pattern matching works for dynamic routes")
    print("✓ Method-specific limits are respected")
    print("✓ Default limits apply to unconfigured routes")
    print("✓ Warning logs are generated for violations")
