"""
Tests for rate limiting middleware implementation.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from fastcore.middleware.rate_limiting import (
    RateLimitConfig,
    RateLimiter,
    SimpleMemoryStore,
    configure_rate_limiting,
    get_client_ip,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        assert config.limit == 100
        assert config.window_seconds == 60
        assert config.block_duration_seconds == 300
        assert config.key_func is None
        assert config.exclude_paths == []

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            limit=50,
            window_seconds=30,
            block_duration_seconds=600,
            key_func="get_client_ip",
            exclude_paths=["/docs", "/health"],
        )
        assert config.limit == 50
        assert config.window_seconds == 30
        assert config.block_duration_seconds == 600
        assert config.key_func == "get_client_ip"
        assert config.exclude_paths == ["/docs", "/health"]

    def test_validation(self):
        """Test validation of time values."""
        # Time values should be positive
        with pytest.raises(ValueError):
            RateLimitConfig(window_seconds=0)

        with pytest.raises(ValueError):
            RateLimitConfig(block_duration_seconds=-1)

        # Valid config should not raise
        config = RateLimitConfig(window_seconds=1, block_duration_seconds=1)
        assert config.window_seconds == 1
        assert config.block_duration_seconds == 1


class TestSimpleMemoryStore:
    """Tests for SimpleMemoryStore."""

    @pytest.fixture
    def store(self):
        """Create a test store."""
        return SimpleMemoryStore()

    def test_add_get_requests(self, store):
        """Test adding and getting requests."""
        # Initially empty
        assert len(store.get_requests("test-client", 60)) == 0

        # Add a request with fixed time
        fixed_time = 1000.0
        with patch("time.time", return_value=fixed_time):
            store.add_request("test-client")
            # Immediately check with mocked time still active
            assert len(store.get_requests("test-client", 60)) == 1

        # Add another request with specific timestamp (30 seconds ago)
        timestamp = fixed_time - 30  # 30 seconds before our fixed time
        store.add_request("test-client", timestamp)

        # Should have two requests now with mocked time
        with patch("time.time", return_value=fixed_time):
            assert len(store.get_requests("test-client", 60)) == 2

        # But only one if window is smaller
        with patch("time.time", return_value=fixed_time):
            assert len(store.get_requests("test-client", 10)) == 1

        # Add old request (outside the window)
        old_timestamp = fixed_time - 120  # 2 minutes ago
        store.add_request("test-client", old_timestamp)

        # Should still only have two requests within the 60s window
        with patch("time.time", return_value=fixed_time):
            assert len(store.get_requests("test-client", 60)) == 2

    def test_block_and_check(self, store):
        """Test blocking and checking blocked status."""
        # Initially not blocked
        assert not store.is_blocked("test-client")
        assert store.get_block_remaining("test-client") == 0

        # Block for 60 seconds
        with patch("time.time", return_value=1000.0):  # Fixed time
            store.block("test-client", 60)

        # Should be blocked now
        with patch("time.time", return_value=1000.0):  # Same fixed time
            assert store.is_blocked("test-client")

            # Remaining time should be close to 60 seconds
            remaining = store.get_block_remaining("test-client")
            assert remaining == 60  # Should be exactly 60 with mocked time

        # Test block expiry
        # Make it seem like time has passed
        with patch("time.time", return_value=1061.0):  # 61 seconds later
            # Should not be blocked anymore
            assert not store.is_blocked("test-client")
            assert store.get_block_remaining("test-client") == 0


class TestRateLimiter:
    """Tests for RateLimiter middleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        @app.get("/excluded")
        def excluded_endpoint():
            return {"message": "excluded from rate limiting"}

        return app

    @pytest.fixture
    def store(self):
        """Create a test memory store."""
        return SimpleMemoryStore()

    def test_should_exempt(self):
        """Test the should_exempt method."""
        # Create a rate limiter with excluded paths
        limiter = RateLimiter(
            None, exclude_paths=["/docs", "/redoc", "/excluded"]  # app
        )

        # Create request mocks
        regular_request = MagicMock()
        regular_request.url.path = "/test"
        regular_request.method = "GET"

        options_request = MagicMock()
        options_request.url.path = "/test"
        options_request.method = "OPTIONS"

        excluded_request = MagicMock()
        excluded_request.url.path = "/excluded"
        excluded_request.method = "GET"

        docs_request = MagicMock()
        docs_request.url.path = "/docs"
        docs_request.method = "GET"

        # Test exemption logic
        assert not limiter.should_exempt(regular_request)  # Not exempted
        assert limiter.should_exempt(options_request)  # OPTIONS are exempted
        assert limiter.should_exempt(excluded_request)  # In excluded paths
        assert limiter.should_exempt(docs_request)  # In excluded paths

    def test_configure_rate_limiting(self):
        """Test the configure_rate_limiting function."""
        app = FastAPI()

        # With default config
        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_rate_limiting(app)

            # Check that middleware was added
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args

            # Check default values
            assert kwargs["limit"] == 100
            assert kwargs["window_seconds"] == 60
            assert kwargs["block_duration_seconds"] == 300

        # With custom config
        mock_add_middleware.reset_mock()
        config = RateLimitConfig(limit=50, window_seconds=30)

        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_rate_limiting(app, config)

            # Check custom values
            args, kwargs = mock_add_middleware.call_args
            assert kwargs["limit"] == 50
            assert kwargs["window_seconds"] == 30

    def test_rate_limiting_integration(self, app, store):
        """Test rate limiting in an integration test."""
        # Configure rate limiting with a low limit
        # Add excluded path explicitly to the app
        app.add_middleware(
            RateLimiter,
            limit=3,  # Allow only 3 requests
            window_seconds=60,
            block_duration_seconds=60,
            store=store,
            exclude_paths=["/excluded"],  # Exclude this path from rate limiting
        )

        client = TestClient(app)

        # First request should succeed
        response = client.get("/test")
        assert response.status_code == 200

        # Second request should succeed
        response = client.get("/test")
        assert response.status_code == 200

        # Third request should succeed (reaching the limit)
        response = client.get("/test")
        assert response.status_code == 200

        # Fourth request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "retry_after" in response.json()

        # Headers should include rate limit info
        assert "retry-after" in response.headers

        # Subsequent requests should also be blocked
        response = client.get("/test")
        assert response.status_code == 429

        # But excluded paths should still work
        response = client.get("/excluded")
        assert response.status_code == 200

    def test_client_ip_function(self):
        """Test the get_client_ip function."""
        # Create request mock
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {}

        # Test direct IP
        assert get_client_ip(request) == "192.168.1.1"

        # Test with X-Forwarded-For header
        request.headers["X-Forwarded-For"] = "10.0.0.1, 10.0.0.2"
        assert get_client_ip(request) == "10.0.0.1"  # Should use first IP

        # Test with proxied IPs
        request.headers[
            "X-Forwarded-For"
        ] = "203.0.113.195, 70.41.3.18, 150.172.238.178"
        assert get_client_ip(request) == "203.0.113.195"  # Should use client IP
