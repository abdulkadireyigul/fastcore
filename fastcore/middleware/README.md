# Middleware Module

This module provides centralized and extensible middleware management for FastAPI applications. It enables easy integration of common middleware such as CORS and rate limiting, with a focus on consistency, configurability, and production readiness.

## Features
- Centralized setup of all application middlewares
- CORS middleware with configurable options
- Rate limiting middleware with memory and Redis backends
- Consistent logging and configuration management
- Extensible structure for adding new middleware types

## Usage

### Factory Integration
The middleware module is automatically integrated when you use the application factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # This will set up all core modules, including middleware
```

### Manual Setup
If you need to customize the setup order or add additional initialization steps:

```python
from fastapi import FastAPI
from fastcore.config import get_settings
from fastcore.logging import ensure_logger
from fastcore.middleware import setup_middlewares

app = FastAPI()
settings = get_settings()
logger = ensure_logger(None, __name__, settings)
setup_middlewares(app, settings, logger)
```

## Configuration
Middleware options are managed via your application's config (see `config/base.py`). Example options:

```python
MIDDLEWARE_CORS_OPTIONS = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
RATE_LIMITING_OPTIONS = {"max_requests": 60, "window_seconds": 60}
RATE_LIMITING_BACKEND = "memory"  # or "redis"
```

## Extending
To add new middleware types:
- Implement your middleware in a new file (e.g., `timing.py`, `i18n.py`).
- Update `setup_middlewares` in `manager.py` to include your new middleware.
- Pass `settings` and `logger` for consistency.

## Logging
All middleware initialization, configuration, and key runtime events are logged using the application's logger for observability and debugging.

## License
MIT
