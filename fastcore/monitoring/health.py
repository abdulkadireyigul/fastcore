"""
Health check functionality for FastAPI applications.

This module provides endpoints and utilities for health checks, 
allowing monitoring systems to verify application status.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, FastAPI, Response, status
from sqlalchemy import text

from fastcore.cache.manager import get_cache
from fastcore.config.base import BaseAppSettings
from fastcore.db import get_db
from fastcore.logging import Logger, ensure_logger
from fastcore.schemas.response import DataResponse, ErrorResponse


class HealthStatus(str, Enum):
    """Health status indicators."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """
    Health check component that can be registered with the health system.

    A health check is a function that returns a status and optional details
    about a specific component of the system (e.g., database, cache).
    """

    def __init__(
        self,
        name: str,
        check_func: Callable[[], Dict[str, Any]],
        tags: List[str] = None,
    ):
        """
        Initialize a health check.

        Args:
            name: Name of the component being checked
            check_func: Async function that performs the check and returns status
            tags: Optional tags for categorizing health checks
        """
        self.name = name
        self.check_func = check_func
        self.tags = tags or []

    async def run(self) -> Dict[str, Any]:
        """
        Run the health check and return the result.

        Returns:
            Dict containing status and any additional details
        """
        try:
            result = await self.check_func()
            return {
                "name": self.name,
                "status": result.get("status", HealthStatus.HEALTHY),
                "details": result.get("details", {}),
                "tags": self.tags,
            }
        except Exception as e:
            return {
                "name": self.name,
                "status": HealthStatus.UNHEALTHY,
                "details": {"error": str(e)},
                "tags": self.tags,
            }


class HealthCheckRegistry:
    """
    Registry for health checks.

    Maintains a collection of health checks that can be executed
    to determine overall system health.
    """

    def __init__(self):
        """Initialize a new health check registry."""
        self.checks: List[HealthCheck] = []

    def register(self, check: HealthCheck) -> None:
        """
        Register a health check.

        Args:
            check: The health check to register
        """
        self.checks.append(check)

    async def run_all(self) -> Dict[str, Any]:
        """
        Run all registered health checks.

        Returns:
            Dict containing overall status and individual check results
        """
        if not self.checks:
            return {"status": HealthStatus.HEALTHY, "checks": []}

        results = []
        overall_status = HealthStatus.HEALTHY

        for check in self.checks:
            result = await check.run()
            results.append(result)

            # Update overall status based on current check
            if result["status"] == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif (
                result["status"] == HealthStatus.DEGRADED
                and overall_status != HealthStatus.UNHEALTHY
            ):
                overall_status = HealthStatus.DEGRADED

        return {"status": overall_status, "checks": results}


# Global registry for health checks
health_registry = HealthCheckRegistry()


async def redis_health_check():
    try:
        cache = await get_cache()
        if cache is None:
            return {
                "status": HealthStatus.UNHEALTHY,
                "details": {"error": "Cache not initialized"},
            }
        pong = await cache.ping()
        return {
            "status": HealthStatus.HEALTHY if pong else HealthStatus.UNHEALTHY,
            "details": {"ping": pong},
        }
    except Exception as e:
        return {"status": HealthStatus.UNHEALTHY, "details": {"error": str(e)}}


async def db_health_check():
    """
    Check database connectivity.

    Returns:
        Health check result for database
    """
    try:
        async for db in get_db():
            result = await db.execute(text("SELECT 1"))
            return {"status": HealthStatus.HEALTHY, "details": {"connected": True}}
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "details": {"error": str(e), "connected": False},
        }


def setup_health_endpoint(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Set up health check endpoints.

    Args:
        app: FastAPI application
        settings: Application settings
        logger: Optional logger
    """
    log = ensure_logger(logger, __name__, settings)

    # Get health check configuration
    health_path = getattr(settings, "HEALTH_PATH", "/health")
    include_details = getattr(settings, "HEALTH_INCLUDE_DETAILS", True)

    # Create router for health endpoints
    router = APIRouter(tags=["monitoring"])

    @router.get(health_path, response_model=DataResponse)
    async def health_check(response: Response):
        """
        Check the health status of the application and its dependencies.

        This endpoint returns the overall health status and (optionally)
        detailed status for each component.

        Returns:
            Health check response with status and component details
        """
        health_result = await health_registry.run_all()

        # Set response status code based on health status
        if health_result["status"] == HealthStatus.UNHEALTHY:
            failed = [
                f"{c['name']} ({c['details'].get('error')})"
                if c["details"].get("error")
                else c["name"]
                for c in health_result["checks"]
                if c["status"] == HealthStatus.UNHEALTHY
            ]
            msg = "Service unhealthy"
            if failed:
                msg += f": {', '.join(failed)}"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return ErrorResponse(
                message=msg,
                data=None,
                metadata={"health": health_result},
            )
        elif health_result["status"] == HealthStatus.DEGRADED:
            response.status_code = status.HTTP_200_OK
        else:
            response.status_code = status.HTTP_200_OK

        # Remove details if not requested
        if not include_details:
            for check in health_result["checks"]:
                check.pop("details", None)

        return DataResponse(data=health_result)

    # Register basic health checks if enabled
    # db_enabled = getattr(settings, "DB_ENABLED", False)
    # if db_enabled:
    health_registry.register(
        HealthCheck(
            name="database", check_func=db_health_check, tags=["core", "database"]
        )
    )

    health_registry.register(
        HealthCheck(name="redis", check_func=redis_health_check, tags=["core", "cache"])
    )

    # Add router to app
    app.include_router(router)
    log.info(f"Health check endpoint configured at {health_path}")
