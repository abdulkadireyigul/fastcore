"""
Example demonstrating the use of FastCore's caching system in a FastAPI application.

This example shows how to:
1. Configure different cache backends (Memory and Redis)
2. Use the @cached decorator to cache function results
3. Use cache invalidation
4. Use caching with FastAPI endpoints

Usage:
    # Run with memory cache:
    python cache_example.py
    
    # Run with Redis cache (requires Redis running):
    CACHE_TYPE=redis python cache_example.py
"""

import os
import random
import time
from typing import Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Query

from fastcore.cache.decorator import cached, invalidate_cache
from fastcore.cache.manager import get_cache_manager
from fastcore.config.app import AppSettings, Environment
from fastcore.factory import create_app


# Create custom settings with the cache type from environment
class CacheExampleSettings(AppSettings):
    """Custom settings for the cache example."""

    def __init__(self):
        """Initialize settings with cache type from environment."""
        super().__init__()

        # Get cache type from environment or use memory as default
        cache_type = os.environ.get("CACHE_TYPE", "memory").lower()
        self.CACHE.CACHE_TYPE = cache_type

        # Set Redis configuration if needed
        if cache_type == "redis":
            self.CACHE.REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
            self.CACHE.REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
            self.CACHE.REDIS_PREFIX = "example:"


# Create the FastAPI application
settings = CacheExampleSettings()
app = create_app(settings=settings)


# Example function that's expensive to compute
@cached(ttl=60)
def compute_expensive_result(input_value: str) -> Dict:
    """
    Simulate an expensive computation that should be cached.

    Args:
        input_value: The input value to process

    Returns:
        A dictionary with the computation result
    """
    print(f"Computing expensive result for input: {input_value}")

    # Simulate an expensive operation
    time.sleep(1)

    return {
        "input": input_value,
        "timestamp": time.time(),
        "random": random.random(),
    }


# Example API routes
@app.get("/cached/{item_id}")
def get_cached_item(item_id: str):
    """
    Get an item with caching applied.

    The expensive computation is cached with the @cached decorator.
    Repeated calls with the same item_id will return the cached result.
    """
    # This call will be cached based on item_id
    result = compute_expensive_result(item_id)

    # Always return fresh metadata
    return {
        "cached_result": result,
        "cache_info": {
            "backend_type": settings.CACHE.CACHE_TYPE,
            "current_time": time.time(),
        },
    }


@app.post("/invalidate/{item_id}")
def invalidate_item_cache(item_id: str):
    """
    Invalidate the cache for a specific item.

    This endpoint demonstrates how to manually invalidate the cache.
    """
    # Invalidate the cache for this item
    invalidated = invalidate_cache(compute_expensive_result, item_id)

    return {
        "item_id": item_id,
        "invalidated": invalidated,
        "timestamp": time.time(),
    }


@app.get("/cache/stats")
def get_cache_stats():
    """
    Get information about the current cache state.

    Returns basic statistics about the cache configuration.
    """
    cache_manager = get_cache_manager()

    # We can't get real stats for Redis from the client interface,
    # so we just return the configuration
    return {
        "backend_type": settings.CACHE.CACHE_TYPE,
        "is_redis": settings.CACHE.CACHE_TYPE == "redis",
        "redis_config": {
            "host": getattr(settings.CACHE, "REDIS_HOST", None),
            "port": getattr(settings.CACHE, "REDIS_PORT", None),
            "prefix": getattr(settings.CACHE, "REDIS_PREFIX", None),
        }
        if settings.CACHE.CACHE_TYPE == "redis"
        else None,
    }


@app.get("/items")
@cached(ttl=30, namespace="api", skip_kwargs=["skip", "limit"])
def get_items(
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Get a list of items with caching applied directly to the API endpoint.

    This endpoint demonstrates caching an entire API response. The skip and limit
    parameters are excluded from the cache key to avoid excessive cache entries.

    Args:
        category: Optional category to filter items
        skip: Number of items to skip (pagination)
        limit: Maximum number of items to return (pagination)
    """
    print(
        f"Generating items list for category: {category}, skip: {skip}, limit: {limit}"
    )

    # Simulate database query
    time.sleep(1)

    # Generate some fake items
    base_items = [
        {"id": i, "name": f"Item {i}", "category": "A" if i % 2 == 0 else "B"}
        for i in range(1, 101)
    ]

    # Filter by category if provided
    if category:
        filtered_items = [item for item in base_items if item["category"] == category]
    else:
        filtered_items = base_items

    # Apply pagination
    result = filtered_items[skip : skip + limit]

    return {
        "items": result,
        "total": len(filtered_items),
        "timestamp": time.time(),
    }


if __name__ == "__main__":
    # Print information about the current configuration
    print(f"Starting cache example with {settings.CACHE.CACHE_TYPE} cache backend")
    if settings.CACHE.CACHE_TYPE == "redis":
        print(
            f"Redis configured at {settings.CACHE.REDIS_HOST}:{settings.CACHE.REDIS_PORT}"
        )

    # Run the application
    uvicorn.run(app, host="127.0.0.1", port=8000)
