# Middleware Module

Provides common middleware components for FastAPI applications with consistent configuration.

## Features

- CORS configuration with sensible defaults
- Rate limiting middleware
- Request timing middleware
- Centralized middleware setup

## Configuration

Configure middleware through environment variables or settings class:

```python
from fastcore.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    # CORS Settings
    CORS_ALLOW_ORIGINS: str = "*"  # Comma-separated list or "*"
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = ""  # Empty means allow all
    CORS_ALLOW_CREDENTIALS: bool = False
    
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

Configure Cross-Origin Resource Sharing:

```python
from fastapi import FastAPI
from fastcore.middleware.cors import configure_cors

app = FastAPI()

# Simple configuration
configure_cors(app, allow_origins=["https://frontend.example.com"])

# Advanced configuration
configure_cors(
    app,
    allow_origins=["https://app.example.com", "https://admin.example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
    max_age=3600
)
```

### Rate Limiting

Protect your API from abuse with rate limiting:

```python
from fastapi import FastAPI
from fastcore.middleware.rate_limiting import configure_rate_limiting

app = FastAPI()

# Basic rate limiting
configure_rate_limiting(app)  # Uses default settings (100 req/minute)

# Custom rate limiting
configure_rate_limiting(
    app,
    limit=50,  # 50 requests per window
    window_seconds=3600,  # 1 hour window
    exclude_paths=["/docs", "/redoc", "/health"],  # Paths to exclude
    key_func=lambda request: request.client.host  # Key function (IP-based)
)
```

## Middleware Components

The following middleware components are available:

- **CORS**: Cross-Origin Resource Sharing configuration
- **Rate Limiting**: Request rate limiting based on client IP or custom key
- **Request Timing**: Add timing headers to responses

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
