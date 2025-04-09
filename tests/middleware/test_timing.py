"""
Tests for request timing middleware implementation.
"""

import time
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastcore.middleware.timing import TimingConfig, TimingMiddleware, configure_timing


class TestTimingConfig:
    """Tests for TimingConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TimingConfig()
        assert config.header_name == "X-Process-Time"
        assert config.exclude_paths == []
        assert config.log_timing is True
        assert config.log_level == "debug"
        assert config.log_threshold_ms is None

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TimingConfig(
            header_name="X-Response-Time",
            exclude_paths=["/docs", "/health"],
            log_timing=False,
            log_level="info",
            log_threshold_ms=100.0,
        )
        assert config.header_name == "X-Response-Time"
        assert config.exclude_paths == ["/docs", "/health"]
        assert config.log_timing is False
        assert config.log_level == "info"
        assert config.log_threshold_ms == 100.0


class TestTimingMiddleware:
    """Tests for TimingMiddleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        @app.get("/slow")
        def slow_endpoint():
            # Simulate a slow response
            time.sleep(0.1)
            return {"message": "slow response"}

        @app.get("/excluded")
        def excluded_endpoint():
            return {"message": "excluded from timing"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_should_process(self):
        """Test the should_process method."""
        # Create a timing middleware with excluded paths
        middleware = TimingMiddleware(
            None, exclude_paths=["/docs", "/redoc", "/excluded"]  # app
        )

        # Create request mocks
        regular_request = MagicMock()
        regular_request.url.path = "/test"

        excluded_request = MagicMock()
        excluded_request.url.path = "/excluded"

        docs_request = MagicMock()
        docs_request.url.path = "/docs"

        # Test processing logic
        assert middleware.should_process(regular_request)  # Should process
        assert not middleware.should_process(excluded_request)  # Should not process
        assert not middleware.should_process(docs_request)  # Should not process

    def test_log_request_time(self):
        """Test the log_request_time method."""
        # Create a middleware with various log level settings
        with patch("fastcore.middleware.timing.logger") as mock_logger:
            # Debug level
            middleware = TimingMiddleware(None, log_level="debug")
            middleware.log_request_time("/test", "GET", 50.0, 200)
            mock_logger.debug.assert_called_once()
            mock_logger.reset_mock()

            # Info level - Create a new instance to avoid initialization logs
            with patch("fastcore.middleware.timing.logger") as mock_info_logger:
                middleware = TimingMiddleware(None, log_level="info")
                # Skip the initialization log message
                mock_info_logger.reset_mock()
                middleware.log_request_time("/test", "GET", 50.0, 200)
                mock_info_logger.info.assert_called_once_with(
                    "Request GET /test took 50.00ms (status: 200)"
                )

            # Warning level
            with patch("fastcore.middleware.timing.logger") as mock_warning_logger:
                middleware = TimingMiddleware(None, log_level="warning")
                mock_warning_logger.reset_mock()
                middleware.log_request_time("/test", "GET", 50.0, 200)
                mock_warning_logger.warning.assert_called_once()

            # Unknown level (should default to debug)
            with patch("fastcore.middleware.timing.logger") as mock_unknown_logger:
                middleware = TimingMiddleware(None, log_level="unknown")
                mock_unknown_logger.reset_mock()
                middleware.log_request_time("/test", "GET", 50.0, 200)
                mock_unknown_logger.debug.assert_called_once()

            # With log_timing=False
            with patch("fastcore.middleware.timing.logger") as mock_disabled_logger:
                middleware = TimingMiddleware(None, log_timing=False)
                middleware.log_request_time("/test", "GET", 50.0, 200)
                mock_disabled_logger.debug.assert_not_called()

            # With threshold
            with patch("fastcore.middleware.timing.logger") as mock_threshold_logger:
                middleware = TimingMiddleware(None, log_threshold_ms=100.0)
                # Below threshold (should not log)
                middleware.log_request_time("/test", "GET", 50.0, 200)
                mock_threshold_logger.debug.assert_not_called()

                # Above threshold (should log)
                middleware.log_request_time("/test", "GET", 150.0, 200)
                mock_threshold_logger.debug.assert_called_once()

    def test_timing_headers_added(self, app, client):
        """Test that timing headers are added to responses."""
        app.add_middleware(TimingMiddleware, header_name="X-Process-Time")

        response = client.get("/test")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        assert "ms" in response.headers["X-Process-Time"]

    def test_path_exclusion(self, app, client):
        """Test that excluded paths don't get timing headers."""
        app.add_middleware(
            TimingMiddleware, header_name="X-Process-Time", exclude_paths=["/excluded"]
        )

        # Regular path should have timing header
        response = client.get("/test")
        assert "X-Process-Time" in response.headers

        # Excluded path should not have timing header
        response = client.get("/excluded")
        assert "X-Process-Time" not in response.headers

    def test_metrics_handler(self, app):
        """Test the metrics handler callback."""
        metrics_handler = MagicMock()
        app.add_middleware(
            TimingMiddleware,
            header_name="X-Process-Time",
            metrics_handler=metrics_handler,
        )

        client = TestClient(app)
        response = client.get("/test")

        # Metrics handler should have been called
        metrics_handler.assert_called_once()
        # First argument should be the path
        assert metrics_handler.call_args[0][0] == "/test"
        # Second argument should be the process time (a float)
        assert isinstance(metrics_handler.call_args[0][1], float)

    def test_metrics_handler_exception(self, app):
        """Test exception handling in metrics handler."""

        def failing_metrics_handler(*args, **kwargs):
            raise ValueError("Simulated error in metrics handler")

        with patch("fastcore.middleware.timing.logger") as mock_logger:
            app.add_middleware(
                TimingMiddleware,
                header_name="X-Process-Time",
                metrics_handler=failing_metrics_handler,
            )

            client = TestClient(app)
            response = client.get("/test")

            # Should log error but not affect response
            assert response.status_code == 200
            mock_logger.error.assert_called_once()

    def test_configure_timing(self):
        """Test the configure_timing function."""
        app = FastAPI()

        # With default config
        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_timing(app)

            # Check that middleware was added
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args

            # Check default values
            assert kwargs["header_name"] == "X-Process-Time"
            assert kwargs["log_timing"] is True

        # With custom config
        mock_add_middleware.reset_mock()
        config = TimingConfig(header_name="X-Response-Time", log_level="info")

        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_timing(app, config)

            # Check custom values
            args, kwargs = mock_add_middleware.call_args
            assert kwargs["header_name"] == "X-Response-Time"
            assert kwargs["log_level"] == "info"

        # With custom metrics handler and direct kwargs
        mock_add_middleware.reset_mock()
        metrics_handler = lambda path, time, req, res: None

        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_timing(
                app, metrics_handler=metrics_handler, log_threshold_ms=500.0
            )

            # Check that handler was passed and kwargs were used
            args, kwargs = mock_add_middleware.call_args
            assert kwargs["metrics_handler"] == metrics_handler
            assert kwargs["log_threshold_ms"] == 500.0
