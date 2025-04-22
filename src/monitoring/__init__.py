"""
Monitoring module for FastAPI applications.

This module provides health checks, metrics collection, and instrumentation
capabilities for monitoring FastAPI applications in production environments.
"""

from src.monitoring.health import setup_health_endpoint
from src.monitoring.manager import setup_monitoring
from src.monitoring.metrics import setup_metrics_endpoint

__all__ = [
    "setup_monitoring",
    "setup_health_endpoint",
    "setup_metrics_endpoint",
]
