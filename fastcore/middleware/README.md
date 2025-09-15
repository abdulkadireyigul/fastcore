# Middleware Module

Provides common middleware components for FastAPI applications with consistent configuration.

## Features

- CORS configuration with sensible defaults
- Rate limiting middleware
- Centralized middleware setup

## Installation

Install the required dependencies:

```bash
poetry add fastapi
```

## Configuration

Configure middleware through environment variables or settings class:

```python
from fastcore.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    # CORS options as a dictionary (recommended)
    MIDDLEWARE_CORS_OPTIONS = {
        "allow_origins": ["*"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
```

## Usage

### Factory Integration

Middleware is automatically set up when using the factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Sets up all middleware based on settings
```

### Manual Configuration

Individually configure middleware components:

```python
from fastapi import FastAPI
from fastcore.middleware import setup_middlewares
from fastcore.config import get_settings
from fastcore.logging import get_logger

app = FastAPI()
settings = get_settings()
logger = get_logger(__name__, settings)

setup_middlewares(app, settings, logger)
```

### CORS Configuration

To add CORS middleware directly:

```python
from fastapi import FastAPI
from fastcore.middleware.cors import add_cors_middleware
from fastcore.config import get_settings
from fastcore.logging import get_logger

app = FastAPI()
settings = get_settings()
logger = get_logger(__name__, settings)
add_cors_middleware(app, settings, logger)
```

### Rate Limiting

The rate limiting middleware provides flexible request rate limiting with support for route-specific configuration.

#### Configuration

Configure through settings:

```python
from fastcore.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    RATE_LIMITING_BACKEND = "redis"  # or "memory"
    RATE_LIMITING_OPTIONS = {
        "max_requests": 60,  # Default requests per window
        "window_seconds": 60,  # Default window size
        "route_config": {
            "/ws": {
                "enabled": False  # Disable rate limiting for WebSocket
            },
            "/api/sensitive": {
                "max_requests": 10,  # Stricter limit
                "window_seconds": 30
            }
        }
    }
```

#### Direct Usage

To add rate limiting middleware directly:

```python
from fastapi import FastAPI
from fastcore.middleware.rate_limiting import add_rate_limiting_middleware
from fastcore.config import get_settings
from fastcore.logging import get_logger

app = FastAPI()
settings = get_settings()
logger = get_logger(__name__, settings)
add_rate_limiting_middleware(app, settings, logger)
```

#### Features

- Support for both memory and Redis backends
- Per-route rate limiting configuration
- Option to disable rate limiting for specific routes
- Rate limit headers (X-RateLimit-*)
- Automatic fallback to memory if Redis is unavailable

#### Production Notes

1. **Redis Backend**
   - Recommended for production/distributed deployments
   - Ensures consistent rate limiting across instances
   - Automatic cleanup via TTL
   - Fallback to memory if Redis is unavailable

2. **Memory Backend**
   - Suitable for development or single-instance deployments
   - No external dependencies
   - Not suitable for distributed setups

## Middleware Components

The following middleware components are available:

- **CORS**: Cross-Origin Resource Sharing configuration
- **Rate Limiting**: Request rate limiting based on client IP or custom key (supports both in-memory and Redis backends; only global, IP-based limits)

## Integration with Logging

Middleware events are logged through the application logger:

```python
from fastapi import FastAPI
from fastcore.logging import get_logger
from fastcore.middleware import setup_middlewares
from fastcore.config import get_settings

app = FastAPI()
settings = get_settings()
logger = get_logger(__name__, settings)

# Middleware will use this logger for events
setup_middlewares(app, settings, logger)
```

## Limitations

- Only CORS and rate limiting middleware are included by default
- Rate limiting is IP-based only (no user-based limits)
- No request timing middleware is implemented
- Middleware configuration is static (no dynamic updates at runtime)
- No built-in support for rate limit monitoring/metrics
