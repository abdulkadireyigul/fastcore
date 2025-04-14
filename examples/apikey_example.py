"""
API Key authentication example using FastCore.

This example demonstrates how to use FastCore's API key security features 
for machine-to-machine authentication scenarios.
"""

from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Security, status
from pydantic import BaseModel

from fastcore.config.base import Environment
from fastcore.factory import create_app
from fastcore.logging import get_logger
from fastcore.security import (
    APIKey,
    APIKeyAuth,
    Permission,
    Role,
    RolePermission,
    get_api_key,
)

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# Application setup
# -----------------------------------------------------------------------------

# Create a FastAPI app
app = create_app(
    env=Environment.DEVELOPMENT,
    title="FastCore API Key Example",
    description="Example of API key authentication with FastCore",
    enable_cors=True,
    enable_error_handlers=True,
)

# -----------------------------------------------------------------------------
# API Key management
# -----------------------------------------------------------------------------

# Create API key manager
api_key_manager = APIKeyAuth()

# Create some example API keys for different services
service_key = api_key_manager.create_api_key(
    name="Service Integration",
    permissions=["items:read", "items:write"],
)

monitoring_key = api_key_manager.create_api_key(
    name="Monitoring Service",
    permissions=["metrics:read", "health:read"],
)

admin_key = api_key_manager.create_api_key(
    name="Admin API",
    permissions=["*:*"],  # All permissions
)

# Print the keys for demonstration (in a real app, store these securely)
logger.info(f"Service API Key: {service_key.api_key}")
logger.info(f"Monitoring API Key: {monitoring_key.api_key}")
logger.info(f"Admin API Key: {admin_key.api_key}")

# -----------------------------------------------------------------------------
# API endpoints
# -----------------------------------------------------------------------------


@app.get("/")
def read_root():
    """Public endpoint that doesn't require authentication."""
    return {"message": "Welcome to the API Key example"}


@app.get("/items/")
def read_items(api_key: APIKey = Depends(get_api_key)):
    """List items (requires API key with items:read permission)."""
    if not api_key.has_permission("items:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key doesn't have items:read permission",
        )

    return [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"},
    ]


@app.post("/items/")
def create_item(api_key: APIKey = Depends(get_api_key)):
    """Create an item (requires API key with items:write permission)."""
    if not api_key.has_permission("items:write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key doesn't have items:write permission",
        )

    return {"message": "Item created"}


@app.get("/metrics/")
def read_metrics(api_key: APIKey = Depends(get_api_key)):
    """Get metrics (requires API key with metrics:read permission)."""
    if not api_key.has_permission("metrics:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key doesn't have metrics:read permission",
        )

    return {
        "active_users": 42,
        "requests_per_minute": 120,
        "average_response_time_ms": 250,
    }


@app.get("/health/")
def read_health(api_key: APIKey = Depends(get_api_key)):
    """Get health status (requires API key with health:read permission)."""
    if not api_key.has_permission("health:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key doesn't have health:read permission",
        )

    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "cache": "connected",
            "queue": "connected",
        },
    }


@app.get("/admin/")
def admin_endpoint(api_key: APIKey = Depends(get_api_key)):
    """Admin endpoint (requires API key with admin permission)."""
    if not api_key.has_permission("admin:access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key doesn't have admin:access permission",
        )

    return {"message": "Admin access granted"}


@app.get("/api-keys/")
def list_api_keys(api_key: APIKey = Depends(get_api_key)):
    """List all API keys (requires API key with admin permission)."""
    if not api_key.has_permission("admin:access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key doesn't have admin:access permission",
        )

    keys = api_key_manager.list_api_keys()
    return [
        {
            "id": key.key_id,
            "name": key.name,
            "enabled": key.enabled,
            "created_at": key.created_at,
            "last_used_at": key.last_used_at,
            "permissions": key.permissions,
        }
        for key in keys
    ]


@app.post("/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: str, api_key: APIKey = Depends(get_api_key)):
    """Revoke an API key (requires API key with admin permission)."""
    if not api_key.has_permission("admin:access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key doesn't have admin:access permission",
        )

    success = api_key_manager.revoke_api_key(key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with ID {key_id} not found",
        )

    return {"message": f"API key {key_id} revoked"}


# Instructions for testing this example
"""
# To test this example, run:
uvicorn apikey_example:app --reload

# Then use curl or a tool like Postman to make requests:

# No API key (should fail)
curl http://localhost:8000/items/

# With Service API key (should work for items endpoints)
curl -H "X-API-Key: <service_key>" http://localhost:8000/items/

# With Service API key for metrics (should fail)
curl -H "X-API-Key: <service_key>" http://localhost:8000/metrics/

# With Monitoring API key for metrics (should work)
curl -H "X-API-Key: <monitoring_key>" http://localhost:8000/metrics/

# With Admin API key (should work for all endpoints)
curl -H "X-API-Key: <admin_key>" http://localhost:8000/admin/
"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
