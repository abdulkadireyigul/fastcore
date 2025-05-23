# Monitoring Module

Provides monitoring, metrics collection, and health check features for FastAPI applications.

## Features

- **Health Checks**: Configurable health check endpoints with component-specific status
- **Metrics Collection**: Prometheus metrics integration for request tracking
- **Correlation/Request ID**: Request tracking with correlation/request IDs (not full distributed tracing)

## Installation

Install the monitoring dependencies:

```bash
poetry add fastapi prometheus_client
```

## Configuration

Configure monitoring through environment variables or settings class:

```python
from fastcore.config import BaseAppSettings

class AppSettings(BaseAppSettings):    
    # Health check settings
    HEALTH_PATH: str = "/health"
    HEALTH_INCLUDE_DETAILS: bool = True
    
    # Metrics settings
    METRICS_PATH: str = "/metrics"
    METRICS_EXCLUDE_PATHS: list = ["/metrics", "/health"]
```

## Usage

### Factory Integration

The monitoring module is automatically set up when using the application factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Sets up monitoring based on settings
```

### Manual Configuration

For more control, configure monitoring components individually:

```python
from fastapi import FastAPI
from fastcore.monitoring import (
    setup_health_endpoint,
    setup_metrics_endpoint,
    setup_monitoring
)
from fastcore.config import get_settings
from fastcore.logging import get_logger

app = FastAPI()
settings = get_settings()
logger = get_logger(__name__, settings)

# Set up health checks
setup_health_endpoint(app, settings, logger)

# Set up metrics collection
setup_metrics_endpoint(app, settings, logger)

# To set up all monitoring features at once:
setup_monitoring(app, settings, logger)
```

### Accessing Health Status

Health checks provide both a basic and detailed status:

```http
GET /health

Response:
{
  "data": {
    "status": "healthy",
    "checks": [
      {
        "name": "database",
        "status": "healthy",
        "details": {
          "connected": true
        },
        "tags": ["core", "database"]
      }
    ]
  }
}
```

### Custom Health Checks

Register custom health checks for application-specific components:

```python
from fastcore.monitoring.health import HealthCheck, HealthStatus, health_registry

# Function that performs the health check
async def redis_health_check():
    try:
        # Check Redis connectivity
        result = await redis.ping()
        return {
            "status": HealthStatus.HEALTHY,
            "details": {"ping": "PONG" if result else "FAILED"}
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "details": {"error": str(e)}
        }

# Register the health check
health_registry.register(
    HealthCheck(
        name="redis",
        check_func=redis_health_check,
        tags=["core", "cache"]
    )
)
```

### Accessing Metrics

Prometheus metrics are exposed at the configured endpoint:

```http
GET /metrics

Response:
# HELP http_requests_total Total count of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/health",status_code="200"} 12
http_requests_total{method="POST",endpoint="/api/users",status_code="201"} 5
...
```

### Correlation/Request ID

Note: The monitoring module does not add a request/correlation ID by default. If you need request IDs for log correlation or response headers, you can add this via custom middleware or use a third-party package. Full distributed tracing (e.g., OpenTelemetry, Jaeger, Zipkin) is not supported.

## Integration with External Tools

The monitoring module is designed for integration with popular monitoring tools:

- **Prometheus**: Metrics are exposed in Prometheus format
- **Grafana**: Create dashboards using the collected metrics
- **ELK/Datadog/etc.**: Log correlation with request IDs

## Limitations

- Only Prometheus metrics and basic health checks are included by default
- No full distributed tracing (e.g., OpenTelemetry, Jaeger, Zipkin)
- No custom metric registration API (only built-in HTTP metrics)
- No built-in alerting or notification features
- Metrics endpoint is public unless protected by other means