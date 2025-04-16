"""
Metrics collection for FastAPI applications.

This module provides tools for collecting and exposing application metrics,
which can be used with monitoring systems like Prometheus.
"""

import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from fastapi import APIRouter, FastAPI, Request, Response
from pydantic import BaseModel, Field

from fastcore.logging import get_logger

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Type of metric."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class Metric:
    """Base class for all metrics."""

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        metric_type: MetricType = None,
    ):
        """
        Initialize a metric.

        Args:
            name: Name of the metric
            description: Description of what the metric measures
            labels: Optional list of label names for this metric
            metric_type: Type of metric (counter, gauge, histogram)
        """
        self.name = name
        self.description = description
        self.labels = labels or []
        self._type = metric_type
        self._values: Dict[tuple, Any] = {}

    def _label_key(self, labels: Dict[str, str]) -> tuple:
        """Convert label dict to a tuple for use as a dictionary key."""
        if not labels:
            return tuple()

        return tuple((key, labels.get(key, "")) for key in sorted(self.labels))

    def get_values(self) -> Dict[str, Dict[tuple, Any]]:
        """Get all values for this metric."""
        return {self.name: self._values}

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for this metric."""
        return {
            "name": self.name,
            "description": self.description,
            "type": self._type.value if self._type else None,
            "labels": self.labels,
        }


class Counter(Metric):
    """A counter metric that can only increase."""

    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        """
        Initialize a counter metric.

        Args:
            name: Name of the metric
            description: Description of what the metric counts
            labels: Optional list of label names for this counter
        """
        super().__init__(name, description, labels, MetricType.COUNTER)

    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment the counter.

        Args:
            value: Value to increment by (must be positive)
            labels: Label values to identify the specific counter
        """
        if value < 0:
            raise ValueError("Counter cannot be decremented")

        labels = labels or {}
        key = self._label_key(labels)

        if key not in self._values:
            self._values[key] = 0.0

        self._values[key] += value


class Gauge(Metric):
    """A gauge metric that can go up and down."""

    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        """
        Initialize a gauge metric.

        Args:
            name: Name of the metric
            description: Description of what the metric measures
            labels: Optional list of label names for this gauge
        """
        super().__init__(name, description, labels, MetricType.GAUGE)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set the gauge to a value.

        Args:
            value: Value to set
            labels: Label values to identify the specific gauge
        """
        labels = labels or {}
        key = self._label_key(labels)
        self._values[key] = value

    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment the gauge.

        Args:
            value: Value to increment by
            labels: Label values to identify the specific gauge
        """
        labels = labels or {}
        key = self._label_key(labels)

        if key not in self._values:
            self._values[key] = 0.0

        self._values[key] += value

    def dec(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Decrement the gauge.

        Args:
            value: Value to decrement by
            labels: Label values to identify the specific gauge
        """
        self.inc(-value, labels)


class HistogramBucket:
    """Helper class for histogram buckets."""

    def __init__(self, upper_bound: float):
        """
        Initialize a histogram bucket.

        Args:
            upper_bound: Upper bound of the bucket
        """
        self.upper_bound = upper_bound
        self.count = 0

    def observe(self, value: float) -> bool:
        """
        Observe a value and increment if it's in this bucket.

        Args:
            value: Value to observe

        Returns:
            True if the value belongs in this bucket, False otherwise
        """
        if value <= self.upper_bound:
            self.count += 1
            return True
        return False


class Histogram(Metric):
    """A histogram metric for measuring distributions of values."""

    def __init__(
        self,
        name: str,
        description: str,
        buckets: List[float] = None,
        labels: Optional[List[str]] = None,
    ):
        """
        Initialize a histogram metric.

        Args:
            name: Name of the metric
            description: Description of what the metric measures
            buckets: List of upper bounds for buckets
            labels: Optional list of label names for this histogram
        """
        super().__init__(name, description, labels, MetricType.HISTOGRAM)
        self.buckets = buckets or [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
        ]
        self._sums: Dict[tuple, float] = {}
        self._counts: Dict[tuple, int] = {}
        self._bucket_values: Dict[tuple, Dict[float, int]] = {}

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Observe a value.

        Args:
            value: Value to observe
            labels: Label values to identify the specific histogram
        """
        labels = labels or {}
        key = self._label_key(labels)

        # Initialize if not exists
        if key not in self._sums:
            self._sums[key] = 0.0
        if key not in self._counts:
            self._counts[key] = 0
        if key not in self._bucket_values:
            self._bucket_values[key] = {b: 0 for b in self.buckets}

        # Update sum and count
        self._sums[key] += value
        self._counts[key] += 1

        # Update buckets
        for bucket in sorted(self.buckets):
            if value <= bucket:
                self._bucket_values[key][bucket] += 1

    def get_values(self) -> Dict[str, Dict[tuple, Any]]:
        """Get all values for this metric."""
        result = {}

        # Add sum values
        result[f"{self.name}_sum"] = self._sums.copy()

        # Add count values
        result[f"{self.name}_count"] = self._counts.copy()

        # Add bucket values
        for bucket in self.buckets:
            bucket_key = f"{self.name}_bucket_{bucket}"
            bucket_values = {}

            for key in self._bucket_values:
                bucket_values[key] = self._bucket_values[key][bucket]

            result[bucket_key] = bucket_values

        return result


class MetricCollector:
    """Collector for application metrics."""

    def __init__(self):
        """Initialize a new metric collector."""
        self._metrics: Dict[str, Metric] = {}

    def register(self, metric: Metric) -> None:
        """
        Register a metric.

        Args:
            metric: The metric to register
        """
        if metric.name in self._metrics:
            raise ValueError(f"Metric '{metric.name}' already registered")

        self._metrics[metric.name] = metric

    def counter(
        self, name: str, description: str, labels: Optional[List[str]] = None
    ) -> Counter:
        """
        Create and register a counter metric.

        Args:
            name: Metric name
            description: Metric description
            labels: List of label names

        Returns:
            A new Counter instance
        """
        counter = Counter(name, description, labels)
        self.register(counter)
        return counter

    def gauge(
        self, name: str, description: str, labels: Optional[List[str]] = None
    ) -> Gauge:
        """
        Create and register a gauge metric.

        Args:
            name: Metric name
            description: Metric description
            labels: List of label names

        Returns:
            A new Gauge instance
        """
        gauge = Gauge(name, description, labels)
        self.register(gauge)
        return gauge

    def histogram(
        self,
        name: str,
        description: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ) -> Histogram:
        """
        Create and register a histogram metric.

        Args:
            name: Metric name
            description: Metric description
            buckets: List of bucket upper bounds
            labels: List of label names

        Returns:
            A new Histogram instance
        """
        hist = Histogram(name, description, buckets, labels)
        self.register(hist)
        return hist

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all registered metrics with their values.

        Returns:
            Dictionary of metrics and their values
        """
        result = {}
        for name, metric in self._metrics.items():
            values = metric.get_values()
            for key, value in values.items():
                result[key] = value
        return result

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata for all registered metrics.

        Returns:
            Dictionary of metric metadata
        """
        result = {}
        for name, metric in self._metrics.items():
            result[name] = metric.get_metadata()
        return result


# Global metric collector
_collector = MetricCollector()


def configure_metrics(
    app: FastAPI, path: str = "/metrics", include_in_schema: bool = True
):
    """
    Configure metrics endpoint for a FastAPI application.

    Args:
        app: FastAPI application
        path: URL path for the metrics endpoint
        include_in_schema: Whether to include in OpenAPI schema

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.monitoring import configure_metrics

        app = FastAPI()
        configure_metrics(app)
        ```
    """
    router = APIRouter()

    @router.get(path, include_in_schema=include_in_schema)
    async def metrics_endpoint():
        """
        Get application metrics.

        Returns:
            A JSON object containing all metrics
        """
        metrics = _collector.get_metrics()
        metadata = _collector.get_metadata()

        # Convert tuple keys to string representation for JSON serialization
        serializable_metrics = {}
        for metric_name, metric_values in metrics.items():
            serializable_values = {}
            for key, value in metric_values.items():
                # Convert tuple key to string representation
                string_key = str(key) if key else "default"
                serializable_values[string_key] = value
            serializable_metrics[metric_name] = serializable_values

        return {"metrics": serializable_metrics, "metadata": metadata}

    app.include_router(router, tags=["system"])
    logger.info(f"Metrics endpoint registered at {path}")

    return _collector


def get_metrics() -> MetricCollector:
    """
    Get the global metrics collector.

    Returns:
        The global MetricCollector instance
    """
    return _collector
