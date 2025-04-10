"""
Health check utilities for FastAPI applications.

This module provides tools for implementing health checks in FastAPI applications,
which are essential for monitoring application health and readiness.
"""

import asyncio
import inspect
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel, Field

from fastcore.logging import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Status of a health check."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResult(BaseModel):
    """Result of a single health check."""

    status: HealthStatus
    name: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = Field(..., description="Time taken to perform the check in ms")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class HealthCheck:
    """Base class for health checks."""

    def __init__(self, name: str):
        """
        Initialize a health check.

        Args:
            name: A unique name for this health check
        """
        self.name = name

    async def __call__(self) -> HealthCheckResult:
        """
        Perform the health check.

        Returns:
            A health check result object
        """
        start_time = time.time()

        try:
            # Execute the check
            result = await self.check()
            duration_ms = (time.time() - start_time) * 1000

            # Return the result
            return HealthCheckResult(
                status=result[0],
                name=self.name,
                details=result[1],
                duration_ms=duration_ms,
            )
        except Exception as e:
            # Handle any exceptions
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check '{self.name}' failed: {str(e)}")

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                name=self.name,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def check(self) -> tuple[HealthStatus, Optional[Dict[str, Any]]]:
        """
        Implement the actual health check logic.

        Returns:
            A tuple of (status, details)
        """
        raise NotImplementedError("Health check implementation required")


class ServiceHealthCheck(HealthCheck):
    """Health check for a service dependency."""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], Union[bool, Dict[str, Any], None]],
        critical: bool = True,
    ):
        """
        Initialize a service health check.

        Args:
            name: Name of the service
            check_func: Function that performs the actual check
            critical: Whether this service is critical (unhealthy if it fails)
        """
        super().__init__(name)
        self.check_func = check_func
        self.critical = critical

    async def check(self) -> tuple[HealthStatus, Dict[str, Any]]:
        """
        Check the service health.

        Returns:
            A tuple of (status, details)
        """
        if asyncio.iscoroutinefunction(self.check_func):
            result = await self.check_func()
        else:
            result = self.check_func()

        if isinstance(result, bool):
            status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
            details = {"available": result}
        elif isinstance(result, dict):
            status = HealthStatus.HEALTHY
            details = result
        else:
            status = HealthStatus.UNHEALTHY
            details = {"error": "Check function returned invalid result"}

        if self.critical and status != HealthStatus.HEALTHY:
            status = HealthStatus.UNHEALTHY
        elif not self.critical and status != HealthStatus.HEALTHY:
            status = HealthStatus.DEGRADED

        return status, details


class HealthResponse(BaseModel):
    """Overall health response model."""

    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    checks: List[HealthCheckResult]
    version: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


def register_health_check(
    app: FastAPI,
    path: str = "/health",
    include_in_schema: bool = True,
    tags: List[str] = ["system"],
):
    """
    Register health check endpoints with a FastAPI application.

    Args:
        app: FastAPI application
        path: URL path for the health check endpoint
        include_in_schema: Whether to include in OpenAPI schema
        tags: OpenAPI tags for the health endpoint

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.monitoring import register_health_check, ServiceHealthCheck

        app = FastAPI()

        # Register a database health check
        async def check_db_connection():
            # Check database connectivity
            return {"connections": 5, "active": 2}

        db_health = ServiceHealthCheck("database", check_db_connection)

        # Register health endpoints with custom health checks
        register_health_check(app, health_checks=[db_health])
        ```
    """
    # Use existing health checks from app state or create new set
    if not hasattr(app.state, "health_checks"):
        app.state.health_checks = set()

    # Create a router for health endpoints
    router = APIRouter(tags=tags)

    @router.get(
        path, response_model=HealthResponse, include_in_schema=include_in_schema
    )
    async def health_check():
        """
        Check the health status of the application and its dependencies.

        Returns:
            A HealthResponse with overall status and individual check results
        """
        results = []

        # Run all health checks
        for check in app.state.health_checks:
            result = await check()
            results.append(result)

        # Determine overall status (worst case)
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            status = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.DEGRADED for r in results):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        # Get version from settings if available
        version = None
        if hasattr(app.state, "settings") and hasattr(app.state.settings, "API"):
            version = getattr(app.state.settings.API, "VERSION", None)

        return HealthResponse(status=status, checks=results, version=version)

    # Add the router to the app
    app.include_router(router)
    logger.info(f"Health check endpoint registered at {path}")

    return router
