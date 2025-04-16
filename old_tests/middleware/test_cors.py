"""
Tests for CORS middleware implementation.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastcore.middleware.cors import CORSConfig, configure_cors


class TestCORSConfig:
    """Tests for CORSConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CORSConfig()
        assert config.allow_origins == ["*"]
        assert "GET" in config.allow_methods
        assert "POST" in config.allow_methods
        assert config.allow_headers == ["*"]
        assert config.allow_credentials is False
        assert config.expose_headers == []
        assert config.max_age == 600

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CORSConfig(
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=True,
            expose_headers=["X-Custom-Header"],
            max_age=3600,
        )

        assert config.allow_origins == ["https://example.com"]
        assert config.allow_methods == ["GET", "POST"]
        assert config.allow_headers == ["Authorization", "Content-Type"]
        assert config.allow_credentials is True
        assert config.expose_headers == ["X-Custom-Header"]
        assert config.max_age == 3600


class TestConfigureCORS:
    """Tests for configure_cors function."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        return FastAPI()

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_configure_cors_default(self, app):
        """Test configuring CORS with default settings."""
        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_cors(app)

            # Check that middleware was added with correct params
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args

            # Check default values
            assert kwargs["allow_origins"] == ["*"]
            assert "GET" in kwargs["allow_methods"]
            assert kwargs["allow_headers"] == ["*"]
            assert kwargs["allow_credentials"] is False

    def test_configure_cors_with_config(self, app):
        """Test configuring CORS with custom config object."""
        config = CORSConfig(
            allow_origins=["https://example.com"], allow_credentials=True, max_age=3600
        )

        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_cors(app, config)

            # Check that middleware was added with correct params
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args

            # Check custom values
            assert kwargs["allow_origins"] == ["https://example.com"]
            assert kwargs["allow_credentials"] is True
            assert kwargs["max_age"] == 3600

    def test_configure_cors_with_kwargs(self, app):
        """Test configuring CORS with direct keyword arguments."""
        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_cors(
                app, allow_origins=["https://api.example.com"], allow_credentials=True
            )

            # Check that middleware was added with correct params
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args

            # Check custom values
            assert kwargs["allow_origins"] == ["https://api.example.com"]
            assert kwargs["allow_credentials"] is True

    def test_cors_integration(self, app, client):
        """Test CORS middleware in an actual request."""
        configure_cors(app, allow_origins=["https://example.com"])

        @app.get("/test-cors")
        def test_endpoint():
            return {"message": "success"}

        # Make a request with CORS headers
        response = client.get("/test-cors", headers={"Origin": "https://example.com"})

        # Check response
        assert response.status_code == 200
        assert response.json() == {"message": "success"}

        # Check CORS headers
        assert response.headers["access-control-allow-origin"] == "https://example.com"

        # Make a request with disallowed origin
        response = client.get(
            "/test-cors", headers={"Origin": "https://unauthorized.com"}
        )

        # Shouldn't have CORS headers for disallowed origin
        assert "access-control-allow-origin" not in response.headers
