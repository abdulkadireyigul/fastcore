"""
Example demonstrating monitoring features in FastCore.

This example shows how to use FastCore's monitoring features to collect metrics,
set up health checks, and instrument application endpoints.
"""

import asyncio
import random
import time
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Query, Request
from pydantic import BaseModel

from fastcore.app_factory import create_app
from fastcore.config.base import Environment
from fastcore.monitoring import (
    HealthCheck,
    HealthStatus,
    ServiceHealthCheck,
    endpoint_metrics,
    get_metrics,
    register_health_check,
)

# Create application with monitoring enabled
app = create_app(
    env=Environment.DEVELOPMENT,
    enable_cors=True,
    enable_error_handlers=True,
    enable_monitoring=True,  # This enables metrics and health checks
    enable_timing=True,  # Optional, but useful for performance insights
)

# Get metrics collector for custom metrics
metrics = get_metrics()

# Define some custom metrics
api_calls_counter = metrics.counter(
    "api_custom_calls_total", "Total number of API calls by feature", ["feature"]
)

business_metric_gauge = metrics.gauge(
    "business_active_users",
    "Number of active users",
)

operation_histogram = metrics.histogram(
    "operation_duration_seconds", "Time spent on operations", labels=["operation_type"]
)

# Set some initial values
business_metric_gauge.set(42)  # Start with 42 active users


# Add a custom service health check
def check_database_health() -> Dict:
    """Simulate a database health check."""
    # In a real app, you'd check your actual database here
    return {"connections": 5, "active_queries": 2, "pool_size": 10}


def check_redis_health() -> bool:
    """Simulate a Redis health check."""
    # In a real app, you'd check Redis connectivity
    return random.random() > 0.1  # 10% chance of failure


# Custom health check implementation
class CustomServiceHealthCheck(HealthCheck):
    """Example custom health check implementation."""

    def __init__(self, name: str, service_url: str):
        super().__init__(name)
        self.service_url = service_url

    async def check(self):
        """Implement the health check logic."""
        try:
            # Simulate a service call with random results
            await asyncio.sleep(0.05)  # Simulate network call

            # 10% chance of degraded, 5% chance of unhealthy
            random_value = random.random()
            if random_value < 0.05:
                return HealthStatus.UNHEALTHY, {
                    "error": "Service unavailable",
                    "url": self.service_url,
                }
            elif random_value < 0.15:
                return HealthStatus.DEGRADED, {
                    "latency_ms": 500,
                    "url": self.service_url,
                    "message": "Service experiencing high latency",
                }
            else:
                return HealthStatus.HEALTHY, {
                    "latency_ms": random.randint(5, 100),
                    "url": self.service_url,
                }
        except Exception as e:
            return HealthStatus.UNHEALTHY, {"error": str(e)}


# Register health checks
db_health = ServiceHealthCheck("database", check_database_health)
redis_health = ServiceHealthCheck("redis", check_redis_health, critical=False)
payment_service = CustomServiceHealthCheck(
    "payment_service", "https://payments.example.com/api"
)

# Add health checks to the app
app.state.health_checks = {db_health, redis_health, payment_service}


# Define API models
class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    stock: int


# Sample data
items = [
    Item(id=1, name="Item 1", description="Description 1", price=10.5, stock=5),
    Item(id=2, name="Item 2", description="Description 2", price=20.0, stock=10),
    Item(id=3, name="Item 3", description="Description 3", price=15.75, stock=3),
]


# API endpoints
@app.get("/", tags=["root"])
async def read_root():
    """Root endpoint to test application."""
    return {"message": "Welcome to the FastCore monitoring example"}


@app.get("/items/", tags=["items"])
@endpoint_metrics(path_name="list_items")  # Track metrics for this specific endpoint
async def read_items(
    request: Request, skip: int = 0, limit: int = Query(default=10, le=100)
):
    """List items with custom metrics collection."""
    api_calls_counter.inc(1, {"feature": "list_items"})

    # Simulate some processing time
    await asyncio.sleep(random.uniform(0.01, 0.05))

    return items[skip : skip + limit]


@app.get("/items/{item_id}", tags=["items"])
async def read_item(item_id: int, request: Request):
    """Get a specific item by ID."""
    api_calls_counter.inc(1, {"feature": "get_item"})

    # Measure operation time
    start_time = time.time()

    # Find the item (with artificial delay)
    await asyncio.sleep(random.uniform(0.02, 0.1))

    item = next((i for i in items if i.id == item_id), None)

    # Record operation time
    duration = time.time() - start_time
    operation_histogram.observe(duration, {"operation_type": "item_lookup"})

    if not item:
        return {"error": "Item not found"}
    return item


@app.post("/items/", tags=["items"])
async def create_item(item: Item):
    """Create a new item with metrics."""
    api_calls_counter.inc(1, {"feature": "create_item"})

    # Simulate processing
    start_time = time.time()
    await asyncio.sleep(random.uniform(0.05, 0.2))

    # Add item to list
    items.append(item)

    # Record operation time
    duration = time.time() - start_time
    operation_histogram.observe(duration, {"operation_type": "item_create"})

    # Increment active users (just for demonstration)
    business_metric_gauge.inc(1)

    return {"status": "created", "id": item.id}


@app.get("/slow", tags=["test"])
async def slow_endpoint():
    """Endpoint that's deliberately slow to demonstrate timing middleware."""
    await asyncio.sleep(0.5)  # 500ms delay
    return {"message": "This was a slow request"}


@app.get("/error", tags=["test"])
async def error_endpoint():
    """Endpoint that generates an error to demonstrate error tracking."""
    if random.random() < 0.75:  # 75% chance of error
        # This will be captured in metrics
        raise ValueError("Random test error")
    return {"message": "No error occurred"}


@app.get("/simulate-load", tags=["test"])
async def simulate_load(requests: int = 10):
    """Generate artificial load for testing metrics."""
    for _ in range(requests):
        feature = random.choice(["list_items", "get_item", "create_item"])
        api_calls_counter.inc(1, {"feature": feature})

    # Update business metrics
    change = random.randint(-5, 10)
    business_metric_gauge.inc(change)

    return {"processed": requests, "user_change": change}


if __name__ == "__main__":
    import uvicorn

    print(
        """
    --------------------------------------------------
    FastCore Monitoring Example
    --------------------------------------------------
    
    Available endpoints:
    - Main API: http://localhost:8000/
    - OpenAPI docs: http://localhost:8000/docs
    - Metrics: http://localhost:8000/metrics
    - Health check: http://localhost:8000/health
    
    Try making some requests to see metrics change!
    """
    )

    uvicorn.run("monitoring_example:app", host="0.0.0.0", port=8000, reload=True)
