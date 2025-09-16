# Middleware Module

Provides common middleware components for FastAPI applications with consistent configuration.

## Features

  - CORS configuration with sensible defaults
  - Advanced rate limiting middleware with **route-based configuration** and **Redis support**
  - Centralized middleware setup

## Installation

Install the required dependencies:

```bash
poetry add fastapi redis
```

## Configuration

Configure middleware through environment variables or a settings class. The rate limiting is now configured using a single dictionary for more flexibility.

```python
from pydantic import Field
from fastcore.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    # CORS options as a dictionary (recommended)
    MIDDLEWARE_CORS_OPTIONS: dict = Field(
        default_factory=lambda: {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    )

    # Rate Limiting
    RATE_LIMITING_BACKEND: str = "memory"  # 'redis' or 'memory'
    RATE_LIMITING_OPTIONS: dict = Field(
        default_factory=lambda: {
            "max_requests": 60,
            "window_seconds": 60,
            "routes": {
                # Method-specific configs
                "POST:/api/users": {"max_requests": 10, "window_seconds": 60},
                "GET:/api/users": {"max_requests": 100, "window_seconds": 60},
                # Any method for this endpoint
                "/api/heavy-endpoint": {"max_requests": 10, "window_seconds": 60},
                # Dynamic routes with method
                "GET:/dzi/{slide_id}_files/{level:int}/{col:int}_{row:int}.jpeg": {
                    "max_requests": 1000,
                    "window_seconds": 60,
                },
                # Disable completely for any method
                "/api/no-limit": {"disabled": True},
            },
        },
        description="Advanced rate limiting options including per-route configurations.",
    )
```

**Note:** For a production environment, it is recommended to define `RATE_LIMITING_OPTIONS` in your `.env` file as a **valid JSON string**.

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

## Middleware Components

The following middleware components are available:

  - **CORS**: Cross-Origin Resource Sharing configuration
  - **Rate Limiting**: Advanced request rate limiting based on client IP. It supports **per-route, per-method configuration** and can be entirely disabled for specific endpoints. It supports both **in-memory** and **Redis backends**.


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

  - Only CORS and rate limiting middleware are included by default.
  - No request timing middleware is implemented.
  - Middleware is set up at startup, not dynamically per request.