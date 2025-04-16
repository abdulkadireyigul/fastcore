"""
Tests for the instrumentation module.
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from fastcore.monitoring.instrumentation import (
    RequestMetrics,
    endpoint_metrics,
    instrument_app,
)
from fastcore.monitoring.metrics import Counter, Gauge, Histogram, MetricCollector


class TestRequestMetricsMiddleware:
    """Tests for the RequestMetrics middleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        return FastAPI()

    @pytest.fixture
    def client(self, app):
        """Create a test client for the app."""
        return TestClient(app)

    @pytest.fixture
    def mock_collector(self):
        """Create a mock metrics collector."""
        mock = MagicMock(spec=MetricCollector)

        # Mock counter, gauge, and histogram
        mock.counter.return_value = MagicMock(spec=Counter)
        mock.gauge.return_value = MagicMock(spec=Gauge)
        mock.histogram.return_value = MagicMock(spec=Histogram)

        return mock

    def test_middleware_initialization(self, app, mock_collector):
        """Test that the middleware initializes correctly."""
        middleware = RequestMetrics(app, metrics_collector=mock_collector)

        # Check that metrics were created
        mock_collector.counter.assert_called_with(
            "http_requests_total",
            "Total number of HTTP requests",
            ["method", "path", "status_code"],
        )

        mock_collector.histogram.assert_called_with(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            ["method", "path", "status_code"],
        )

        mock_collector.gauge.assert_called_with(
            "http_requests_in_progress",
            "Number of HTTP requests currently in progress",
            ["method"],
        )

        assert middleware.exclude_paths == ["/metrics", "/health"]

    def test_should_process(self, app):
        """Test the should_process method."""
        middleware = RequestMetrics(app)

        # Create mock requests
        metric_request = MagicMock(spec=Request)
        metric_request.url.path = "/metrics"

        health_request = MagicMock(spec=Request)
        health_request.url.path = "/health"

        api_request = MagicMock(spec=Request)
        api_request.url.path = "/api/users"

        # Check processing logic
        assert not middleware.should_process(metric_request)
        assert not middleware.should_process(health_request)
        assert middleware.should_process(api_request)

    @pytest.mark.asyncio
    async def test_dispatch_successful_request(self, app, mock_collector):
        """Test the dispatch method with a successful request."""
        # Create metrics mocks
        request_count = MagicMock(spec=Counter)
        request_duration = MagicMock(spec=Histogram)
        requests_in_progress = MagicMock(spec=Gauge)

        mock_collector.counter.return_value = request_count
        mock_collector.histogram.return_value = request_duration
        mock_collector.gauge.return_value = requests_in_progress

        # Create middleware
        middleware = RequestMetrics(app, metrics_collector=mock_collector)
        middleware.request_count = request_count
        middleware.request_duration = request_duration
        middleware.requests_in_progress = requests_in_progress

        # Create mock request with scope
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/users"
        request.scope = {"method": "GET", "path": "/api/users"}

        # Mock route matching
        mock_route = MagicMock()
        mock_route.path = "/api/users"
        mock_route.matches.return_value = (True, {})

        # Create a mock app with routes attribute
        mock_app = MagicMock()
        mock_app.routes = [mock_route]
        request.app = mock_app

        # Mock response
        response = MagicMock()
        response.status_code = 200

        # Mock call_next
        async def mock_call_next(_request):
            return response

        # Dispatch the request
        result = await middleware.dispatch(request, mock_call_next)

        # Verify metrics were recorded
        requests_in_progress.inc.assert_called_with(1, {"method": "GET"})
        requests_in_progress.dec.assert_called_with(1, {"method": "GET"})

        request_count.inc.assert_called_with(
            1, {"method": "GET", "path": "/api/users", "status_code": "200"}
        )

        request_duration.observe.assert_called_once()
        assert result == response

    @pytest.mark.asyncio
    async def test_dispatch_error_request(self, app, mock_collector):
        """Test the dispatch method with an error request."""
        # Create metrics mocks
        request_count = MagicMock(spec=Counter)
        request_duration = MagicMock(spec=Histogram)
        requests_in_progress = MagicMock(spec=Gauge)

        mock_collector.counter.return_value = request_count
        mock_collector.histogram.return_value = request_duration
        mock_collector.gauge.return_value = requests_in_progress

        # Create middleware
        middleware = RequestMetrics(app, metrics_collector=mock_collector)
        middleware.request_count = request_count
        middleware.request_duration = request_duration
        middleware.requests_in_progress = requests_in_progress

        # Create mock request with scope
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/users"
        request.scope = {"method": "POST", "path": "/api/users"}

        # Mock route matching
        mock_route = MagicMock()
        mock_route.path = "/api/users"
        mock_route.matches.return_value = (True, {})

        # Create a mock app with routes attribute
        mock_app = MagicMock()
        mock_app.routes = [mock_route]
        request.app = mock_app

        # Mock call_next to raise an exception
        async def mock_call_next(_request):
            raise ValueError("Test error")

        # Dispatch the request
        with pytest.raises(ValueError):
            await middleware.dispatch(request, mock_call_next)

        # Verify metrics were recorded
        requests_in_progress.inc.assert_called_with(1, {"method": "POST"})
        requests_in_progress.dec.assert_called_with(1, {"method": "POST"})

        request_count.inc.assert_called_with(
            1, {"method": "POST", "path": "/api/users", "status_code": "500"}
        )

        request_duration.observe.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_exclude_paths(self, app, mock_collector):
        """Test the dispatch method with excluded paths."""
        # Create middleware
        middleware = RequestMetrics(app, metrics_collector=mock_collector)

        # Create mock request for an excluded path
        request = MagicMock(spec=Request)
        request.url.path = "/metrics"

        # Mock response
        response = MagicMock()

        # Mock call_next
        async def mock_call_next(_request):
            return response

        # Dispatch the request
        result = await middleware.dispatch(request, mock_call_next)

        # Verify no metrics were recorded (pass-through)
        mock_collector.counter.return_value.inc.assert_not_called()
        assert result == response


class TestEndpointMetricsDecorator:
    """Tests for the endpoint_metrics decorator."""

    @pytest.mark.asyncio
    async def test_decorator_wraps_function(self):
        """Test that the decorator properly wraps the function."""
        # Create mock collector and histogram
        mock_collector = MagicMock(spec=MetricCollector)
        mock_histogram = MagicMock(spec=Histogram)
        mock_collector.histogram.return_value = mock_histogram

        # Define a test function to decorate
        @endpoint_metrics(path_name="test_endpoint", metrics_collector=mock_collector)
        async def test_function(a, b):
            return a + b

        # Check that the original function metadata is preserved
        assert test_function.__name__ == "test_function"

        # Check that the metric was created
        mock_collector.histogram.assert_called_with(
            "endpoint_test_endpoint_duration_seconds",
            "Duration of test_endpoint endpoint in seconds",
        )

        # Test the wrapped function
        result = await test_function(1, 2)

        # Check the result and metric observation
        assert result == 3
        mock_histogram.observe.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_default_name(self):
        """Test that the decorator uses function name if path_name not provided."""
        # Create mock collector
        mock_collector = MagicMock(spec=MetricCollector)

        # Define a test function with default name
        @endpoint_metrics(metrics_collector=mock_collector)
        async def custom_function():
            return "result"

        # Check that the metric was created with the function name
        mock_collector.histogram.assert_called_with(
            "endpoint_custom_function_duration_seconds",
            "Duration of custom_function endpoint in seconds",
        )

    @pytest.mark.asyncio
    async def test_decorator_with_exception(self):
        """Test that the decorator captures metrics even when the function raises an exception."""
        # Create mock collector and histogram
        mock_collector = MagicMock(spec=MetricCollector)
        mock_histogram = MagicMock(spec=Histogram)
        mock_collector.histogram.return_value = mock_histogram

        # Define a test function that raises an exception
        @endpoint_metrics(path_name="error_endpoint", metrics_collector=mock_collector)
        async def failing_function():
            raise ValueError("Test error")

        # Call the function
        with pytest.raises(ValueError):
            await failing_function()

        # Check that the metric was recorded despite the exception
        mock_histogram.observe.assert_called_once()


class TestInstrumentApp:
    """Tests for the instrument_app function."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        return FastAPI()

    @patch("fastcore.monitoring.metrics.configure_metrics")
    @patch("fastcore.monitoring.health.register_health_check")
    @patch("fastcore.middleware.timing.configure_timing")
    def test_instrument_app_basic(self, mock_timing, mock_health, mock_metrics, app):
        """Test the basic instrumentation of an app."""
        # Call the function
        result = instrument_app(app)

        # Check that metrics endpoint was configured
        mock_metrics.assert_called_with(app, path="/metrics")

        # Check that health check was registered
        mock_health.assert_called_with(app, path="/health")

        # Check that timing middleware was added
        mock_timing.assert_called_once()

        # Check that the function returns the app
        assert result == app

        # We can't directly check the middleware stack in a test
        # because it's built on first request, but we can check the app routes
        assert len(app.routes) > 0

    @patch("fastcore.monitoring.metrics.configure_metrics")
    @patch("fastcore.monitoring.health.register_health_check")
    @patch("fastcore.middleware.timing.configure_timing")
    def test_instrument_app_no_timing(
        self, mock_timing, mock_health, mock_metrics, app
    ):
        """Test instrumenting an app without timing middleware."""
        # Call the function
        instrument_app(app, add_timing_middleware=False)

        # Check that timing middleware was not added
        mock_timing.assert_not_called()

    @patch("fastcore.monitoring.metrics.configure_metrics")
    @patch("fastcore.monitoring.health.register_health_check")
    @patch("fastcore.middleware.timing.configure_timing")
    def test_instrument_app_custom_paths(
        self, mock_timing, mock_health, mock_metrics, app
    ):
        """Test instrumenting an app with custom paths."""
        # Call the function with custom paths
        instrument_app(
            app,
            metrics_path="/custom/metrics",
            health_path="/custom/health",
            exclude_paths=["/custom/exclude"],
        )

        # Check that custom paths were used
        mock_metrics.assert_called_with(app, path="/custom/metrics")
        mock_health.assert_called_with(app, path="/custom/health")

        # Check that exclude paths were properly set
        expected_exclude = [
            "/custom/exclude",
            "/metrics",
            "/health",
            "/openapi.json",
            "/docs",
            "/redoc",
        ]

        # Check that timing config received the custom exclude paths
        mock_timing.assert_called_once()
        _, kwargs = mock_timing.call_args
        assert sorted(kwargs["exclude_paths"]) == sorted(expected_exclude)

    @patch("fastcore.monitoring.metrics._collector")
    def test_instrument_app_integration(self, mock_collector, app):
        """Test the full integration of instrumented app features."""
        # Create a fresh metrics collector for this test
        mock_collector = MagicMock()
        mock_collector.counter.return_value = MagicMock(spec=Counter)
        mock_collector.histogram.return_value = MagicMock(spec=Histogram)
        mock_collector.gauge.return_value = MagicMock(spec=Gauge)

        # Create a simple health endpoint implementation
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        # Create a simple metrics endpoint implementation
        @app.get("/metrics")
        async def metrics_endpoint():
            return {"metrics": {}, "metadata": {}}

        # Add a test endpoint
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        # Create test client
        client = TestClient(app)

        # Check that health endpoint works
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert "status" in health_response.json()

        # Check that metrics endpoint works
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "metrics" in metrics_response.json()

        # Check that regular endpoint works
        test_response = client.get("/test")
        assert test_response.status_code == 200
        assert test_response.json() == {"status": "ok"}
