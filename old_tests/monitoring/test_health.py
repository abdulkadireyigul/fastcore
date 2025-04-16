"""
Tests for the health check module.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastcore.monitoring.health import (
    HealthCheck,
    HealthCheckResult,
    HealthStatus,
    ServiceHealthCheck,
    register_health_check,
)


class TestHealthStatus:
    """Tests for the HealthStatus enum."""

    def test_health_status_values(self):
        """Test that the health status enum has the expected values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestHealthCheckResult:
    """Tests for the HealthCheckResult model."""

    def test_health_check_result_init(self):
        """Test that health check results can be created properly."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            name="test_check",
            details={"key": "value"},
            duration_ms=10.5,
        )

        assert result.status == HealthStatus.HEALTHY
        assert result.name == "test_check"
        assert result.details == {"key": "value"}
        assert result.duration_ms == 10.5
        assert result.error is None
        assert result.timestamp is not None


class TestServiceHealthCheck:
    """Tests for the ServiceHealthCheck class."""

    @pytest.mark.asyncio
    async def test_service_check_success(self):
        """Test a successful service health check."""

        def check_func():
            return {"status": "ok", "connections": 5}

        health_check = ServiceHealthCheck("test_service", check_func)
        status, details = await health_check.check()

        assert status == HealthStatus.HEALTHY
        assert details == {"status": "ok", "connections": 5}

    @pytest.mark.asyncio
    async def test_service_check_failure(self):
        """Test a failed service health check."""

        def check_func():
            return False

        health_check = ServiceHealthCheck("test_service", check_func)
        status, details = await health_check.check()

        assert status == HealthStatus.UNHEALTHY
        assert details == {"available": False}

    @pytest.mark.asyncio
    async def test_service_check_non_critical_failure(self):
        """Test a failed non-critical service health check."""

        def check_func():
            return False

        health_check = ServiceHealthCheck("test_service", check_func, critical=False)
        status, details = await health_check.check()

        assert status == HealthStatus.DEGRADED
        assert details == {"available": False}

    @pytest.mark.asyncio
    async def test_service_check_exception(self):
        """Test a service health check that raises an exception."""

        def check_func():
            raise ValueError("Test error")

        health_check = ServiceHealthCheck("test_service", check_func)
        result = await health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "Test error"
        assert result.duration_ms > 0


# Test implementation moved outside to avoid pytest warnings
class HealthCheckTestImpl(HealthCheck):
    """Test implementation of HealthCheck."""

    def __init__(self, name: str, status: HealthStatus, details=None):
        super().__init__(name)
        self.return_status = status
        self.return_details = details or {}

    async def check(self):
        return self.return_status, self.return_details


class TestHealthCheck:
    """Tests for the base HealthCheck class."""

    @pytest.mark.asyncio
    async def test_health_check_call(self):
        """Test calling a health check implementation."""
        check = HealthCheckTestImpl("test", HealthStatus.HEALTHY, {"test": "value"})

        result = await check()

        assert result.status == HealthStatus.HEALTHY
        assert result.name == "test"
        assert result.details == {"test": "value"}
        assert result.error is None
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """Test a health check that raises an exception."""

        class ErrorHealthCheck(HealthCheck):
            def __init__(self, name: str):
                super().__init__(name)

            async def check(self):
                raise ValueError("Test error")

        check = ErrorHealthCheck("test_error")
        result = await check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.name == "test_error"
        assert result.error == "Test error"
        assert result.duration_ms > 0


class TestRegisterHealthCheck:
    """Tests for the register_health_check function."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        return FastAPI()

    @pytest.fixture
    def client(self, app):
        """Create a test client for the app."""
        return TestClient(app)

    def test_register_health_check(self, app, client):
        """Test registering health check endpoints."""
        # Create and register some health checks
        healthy_check = HealthCheckTestImpl(
            "healthy_service", HealthStatus.HEALTHY, {"status": "ok"}
        )

        unhealthy_check = HealthCheckTestImpl(
            "unhealthy_service",
            HealthStatus.UNHEALTHY,
            {"error": "Service unavailable"},
        )

        app.state.health_checks = {healthy_check, unhealthy_check}

        router = register_health_check(app, path="/api/health")

        # Test the health endpoint
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "unhealthy"  # Overall status is the worst check
        assert len(data["checks"]) == 2

        # Check healthy service details
        healthy_result = next(
            c for c in data["checks"] if c["name"] == "healthy_service"
        )
        assert healthy_result["status"] == "healthy"
        assert healthy_result["details"] == {"status": "ok"}

        # Check unhealthy service details
        unhealthy_result = next(
            c for c in data["checks"] if c["name"] == "unhealthy_service"
        )
        assert unhealthy_result["status"] == "unhealthy"
        assert unhealthy_result["details"] == {"error": "Service unavailable"}
