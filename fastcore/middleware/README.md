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
- Rate limiting supports both in-memory and Redis backends, but only global, IP-based limits (no per-route or user-based rate limiting)
- No request timing middleware is implemented (despite earlier mention)
- Middleware is set up at startup, not dynamically per request
- Advanced CORS and rate limiting features (e.g., per-route config, custom backends) are not included
