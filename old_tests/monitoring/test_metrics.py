"""
Tests for the metrics collection module.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastcore.monitoring.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricCollector,
    MetricType,
    configure_metrics,
    get_metrics,
)


class TestMetricTypes:
    """Tests for the metric classes."""

    def test_counter_increments(self):
        """Test that a counter can be incremented."""
        counter = Counter("test_counter", "A test counter", ["label1", "label2"])

        # Test incrementing with no labels
        counter.inc()
        assert counter._values[()] == 1.0

        # Test incrementing with labels
        counter.inc(1.5, {"label1": "value1", "label2": "value2"})
        assert counter._values[(("label1", "value1"), ("label2", "value2"))] == 1.5

        # Test incrementing again
        counter.inc(2.0, {"label1": "value1", "label2": "value2"})
        assert counter._values[(("label1", "value1"), ("label2", "value2"))] == 3.5

    def test_counter_negative_value(self):
        """Test that a counter cannot be decremented."""
        counter = Counter("test_counter", "A test counter")

        with pytest.raises(ValueError):
            counter.inc(-1.0)

    def test_gauge_operations(self):
        """Test gauge set, increment and decrement operations."""
        gauge = Gauge("test_gauge", "A test gauge", ["label"])

        # Test setting with no labels
        gauge.set(5.0)
        assert gauge._values[()] == 5.0

        # Test setting with labels
        gauge.set(10.0, {"label": "value"})
        assert gauge._values[(("label", "value"),)] == 10.0

        # Test incrementing
        gauge.inc(2.0, {"label": "value"})
        assert gauge._values[(("label", "value"),)] == 12.0

        # Test decrementing
        gauge.dec(5.0, {"label": "value"})
        assert gauge._values[(("label", "value"),)] == 7.0

        # Test decrementing below zero
        gauge.dec(10.0, {"label": "value"})
        assert gauge._values[(("label", "value"),)] == -3.0

    def test_histogram_observations(self):
        """Test histogram observations."""
        buckets = [1.0, 5.0, 10.0]
        hist = Histogram("test_histogram", "A test histogram", buckets)

        # Make some observations
        hist.observe(0.5)  # Falls in first bucket
        hist.observe(3.0)  # Falls in second bucket
        hist.observe(7.0)  # Falls in third bucket
        hist.observe(15.0)  # Above all buckets

        # Check the sum
        sum_values = hist.get_values()["test_histogram_sum"]
        assert sum_values[()] == 0.5 + 3.0 + 7.0 + 15.0

        # Check the count
        count_values = hist.get_values()["test_histogram_count"]
        assert count_values[()] == 4

        # Check the buckets
        bucket_values = hist.get_values()
        assert bucket_values["test_histogram_bucket_1.0"][()] == 1  # 0.5 only
        assert bucket_values["test_histogram_bucket_5.0"][()] == 2  # 0.5, 3.0
        assert bucket_values["test_histogram_bucket_10.0"][()] == 3  # 0.5, 3.0, 7.0

    def test_histogram_with_labels(self):
        """Test histogram with labels."""
        buckets = [1.0, 5.0, 10.0]
        hist = Histogram("test_histogram", "A test histogram", buckets, ["method"])

        # Make some observations with different labels
        hist.observe(0.5, {"method": "GET"})
        hist.observe(3.0, {"method": "GET"})
        hist.observe(7.0, {"method": "POST"})

        # Check the sums
        sum_values = hist.get_values()["test_histogram_sum"]
        assert sum_values[(("method", "GET"),)] == 0.5 + 3.0
        assert sum_values[(("method", "POST"),)] == 7.0

        # Check the counts
        count_values = hist.get_values()["test_histogram_count"]
        assert count_values[(("method", "GET"),)] == 2
        assert count_values[(("method", "POST"),)] == 1

        # Check the buckets for GET
        bucket_values = hist.get_values()
        assert (
            bucket_values["test_histogram_bucket_1.0"][(("method", "GET"),)] == 1
        )  # 0.5 only
        assert (
            bucket_values["test_histogram_bucket_5.0"][(("method", "GET"),)] == 2
        )  # 0.5, 3.0


class TestMetricCollector:
    """Tests for the MetricCollector class."""

    def test_collector_registration(self):
        """Test registering metrics with a collector."""
        collector = MetricCollector()

        counter = Counter("test_counter", "A test counter")
        collector.register(counter)

        # Test duplicate registration
        with pytest.raises(ValueError):
            collector.register(Counter("test_counter", "Duplicate counter"))

    def test_collector_convenience_methods(self):
        """Test the convenience methods for creating metrics."""
        collector = MetricCollector()

        # Create metrics using convenience methods
        counter = collector.counter("test_counter", "A test counter")
        gauge = collector.gauge("test_gauge", "A test gauge")
        hist = collector.histogram("test_hist", "A test histogram")

        # Test that they're the right types
        assert isinstance(counter, Counter)
        assert isinstance(gauge, Gauge)
        assert isinstance(hist, Histogram)

        # Test that they're registered
        assert "test_counter" in collector._metrics
        assert "test_gauge" in collector._metrics
        assert "test_hist" in collector._metrics

    def test_get_metrics(self):
        """Test getting all metrics from a collector."""
        collector = MetricCollector()

        # Add some metrics
        counter = collector.counter("counter", "A counter")
        gauge = collector.gauge("gauge", "A gauge")

        # Set some values
        counter.inc(5)
        gauge.set(10)

        # Get all metrics
        metrics = collector.get_metrics()

        # Check the values
        assert metrics["counter"][()] == 5
        assert metrics["gauge"][()] == 10

    def test_get_metadata(self):
        """Test getting metadata about metrics."""
        collector = MetricCollector()

        # Add some metrics
        collector.counter("counter", "A counter", ["label"])
        collector.gauge("gauge", "A gauge")

        # Get metadata
        metadata = collector.get_metadata()

        # Check metadata
        assert metadata["counter"]["name"] == "counter"
        assert metadata["counter"]["description"] == "A counter"
        assert metadata["counter"]["type"] == "counter"
        assert metadata["counter"]["labels"] == ["label"]

        assert metadata["gauge"]["name"] == "gauge"
        assert metadata["gauge"]["description"] == "A gauge"
        assert metadata["gauge"]["type"] == "gauge"
        assert metadata["gauge"]["labels"] == []


class TestConfigureMetrics:
    """Tests for the configure_metrics function."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        return FastAPI()

    @pytest.fixture
    def client(self, app):
        """Create a test client for the app."""
        return TestClient(app)

    def test_configure_metrics(self, app, client):
        """Test configuring metrics endpoint."""
        collector = configure_metrics(app, path="/api/metrics")

        # Add a metric to ensure it appears
        counter = collector.counter("test_counter", "Test counter")
        counter.inc(42)

        # Test the metrics endpoint
        response = client.get("/api/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "metrics" in data
        assert "metadata" in data
        assert "test_counter" in data["metadata"]
        # Check the value using the string-based key (empty tuple becomes "default")
        assert data["metrics"]["test_counter"]["default"] == 42

    def test_get_metrics_global(self):
        """Test getting the global metrics collector."""
        collector = get_metrics()

        # Add a metric to ensure it's the same instance
        counter = collector.counter("global_counter", "Global counter")
        counter.inc(42)

        # Get the collector again
        collector2 = get_metrics()

        # Should be the same instance with the same metric
        assert "global_counter" in collector2._metrics
        assert collector2._metrics["global_counter"] == counter

        # Check the counter value
        metrics = collector2.get_metrics()
        assert metrics["global_counter"][()] == 42
