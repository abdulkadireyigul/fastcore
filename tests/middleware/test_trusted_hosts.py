"""
Tests for trusted hosts middleware implementation.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastcore.middleware.trusted_hosts import (
    TrustedHostMiddleware,
    TrustedHostsConfig,
    configure_trusted_hosts,
)


class TestTrustedHostsConfig:
    """Tests for TrustedHostsConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TrustedHostsConfig()
        assert config.allowed_hosts == ["*"]
        assert config.www_redirect is True
        assert config.https_redirect is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TrustedHostsConfig(
            allowed_hosts=["example.com", "api.example.com"],
            www_redirect=False,
            https_redirect=True,
        )
        assert config.allowed_hosts == ["example.com", "api.example.com"]
        assert config.www_redirect is False
        assert config.https_redirect is True

    def test_wildcard_validation(self):
        """Test validation of wildcard usage."""
        # Valid: single wildcard
        config = TrustedHostsConfig(allowed_hosts=["*"])
        assert config.allowed_hosts == ["*"]

        # Valid: multiple specific hosts
        config = TrustedHostsConfig(allowed_hosts=["example.com", "api.example.com"])
        assert config.allowed_hosts == ["example.com", "api.example.com"]

        # Invalid: wildcard with other hosts
        with pytest.raises(ValueError):
            TrustedHostsConfig(allowed_hosts=["*", "example.com"])


class TestTrustedHostMiddleware:
    """Tests for TrustedHostMiddleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client for the app."""
        return TestClient(app, base_url="http://testserver")

    def test_compile_patterns(self):
        """Test the pattern compilation."""
        # Setup middleware with specific hosts
        middleware = TrustedHostMiddleware(
            None, allowed_hosts=["example.com", "*.api.example.com"]
        )

        # Check wildcard pattern
        assert len(middleware.host_patterns) == 2
        assert middleware._is_host_allowed("example.com")
        assert middleware._is_host_allowed("sub.api.example.com")
        assert middleware._is_host_allowed("v1.api.example.com")
        assert not middleware._is_host_allowed("other.com")
        assert not middleware._is_host_allowed(
            "api.example.com"
        )  # Doesn't match *.api.example.com

        # Check with wildcard allowed_hosts
        middleware = TrustedHostMiddleware(None, allowed_hosts=["*"])
        assert middleware._is_host_allowed("any.domain.com")
        assert middleware._is_host_allowed("example.com")

    def test_host_validation(self, app, client):
        """Test host validation functionality."""
        # Configure middleware with specific allowed hosts
        app.add_middleware(
            TrustedHostMiddleware, allowed_hosts=["testserver", "example.com"]
        )

        # Valid host (testserver is the default test host)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}

        # Invalid host (simulated via override_headers)
        response = client.get("/test", headers={"host": "invalid.com"})
        assert response.status_code == 400
        assert response.text == "Invalid host header"

    def test_www_redirect(self, app):
        """Test www to non-www redirection."""
        # Configure middleware with www redirection enabled
        # IMPORTANT: We must include both www.example.com AND example.com in allowed_hosts
        # Otherwise, the middleware will reject www.example.com before it can redirect
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com", "www.example.com"],
            www_redirect=True,
        )

        # Create client with www domain
        client = TestClient(app, base_url="http://www.example.com")

        # Should redirect to non-www
        response = client.get("/test", follow_redirects=False)
        assert response.status_code == 301
        assert response.headers["location"] == "http://example.com/test"

    def test_https_redirect(self, app):
        """Test HTTP to HTTPS redirection."""
        # Configure middleware with HTTPS redirection enabled
        app.add_middleware(
            TrustedHostMiddleware, allowed_hosts=["example.com"], https_redirect=True
        )

        # Create client with HTTP scheme
        client = TestClient(app, base_url="http://example.com")

        # Should redirect to HTTPS
        response = client.get("/test", follow_redirects=False)
        assert response.status_code == 301
        assert response.headers["location"] == "https://example.com/test"

    def test_configure_trusted_hosts(self):
        """Test the configure_trusted_hosts function."""
        app = FastAPI()

        # With default config
        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_trusted_hosts(app)

            # Check that middleware was added
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args

            # Check default values
            assert kwargs["allowed_hosts"] == ["*"]
            assert kwargs["www_redirect"] is True
            assert kwargs["https_redirect"] is False

        # With custom config
        mock_add_middleware.reset_mock()
        config = TrustedHostsConfig(allowed_hosts=["example.com"], https_redirect=True)

        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_trusted_hosts(app, config)

            # Check that middleware was added with custom values
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args
            assert kwargs["allowed_hosts"] == ["example.com"]
            assert kwargs["https_redirect"] is True

        # With direct kwargs
        mock_add_middleware.reset_mock()
        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_trusted_hosts(
                app, allowed_hosts=["api.example.com"], www_redirect=False
            )

            # Check that middleware was added with custom values
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args
            assert kwargs["allowed_hosts"] == ["api.example.com"]
            assert kwargs["www_redirect"] is False
