# Config Module

Configuration management for FastAPI applications that provides a simple, environment-aware settings system using Pydantic.

## Features

- Environment-based configuration with development, testing, and production profiles
- Based on Pydantic for schema validation and type safety
- Easy access to settings via dependency injection
- Environment variable loading with proper type conversion
- Support for `.env` files

## Installation

Install Pydantic and pydantic-settings:

```bash
poetry add pydantic pydantic-settings
```

## Usage

### Basic Usage

In your application, access settings through the dependency:

```python
from fastapi import FastAPI, Depends
from fastcore.config import get_settings

app = FastAPI()

@app.get("/info")
async def get_info(settings = Depends(get_settings)):
    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "debug": settings.DEBUG
    }
```

### Custom Settings

Create custom settings by extending `BaseAppSettings`:

```python
from fastcore.config import BaseAppSettings

class MyAppSettings(BaseAppSettings):
    # Add custom settings
    FEATURE_FLAG_ENABLED: bool = False
    MAX_ITEMS_PER_PAGE: int = 100
    
    # Override base settings
    APP_NAME: str = "My Custom App"
```

### Using Custom Settings in Your App

To use your custom settings class (`MyAppSettings`) in your FastAPI application, pass an instance to the factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app
from myproject.config import MyAppSettings  # Adjust import as needed

app = FastAPI()
custom_settings = MyAppSettings()
configure_app(app, settings=custom_settings)
```

Or, if you want to use it with dependency injection:

```python
from fastapi import Depends
from myproject.config import MyAppSettings

my_settings = MyAppSettings()

def get_custom_settings():
    return my_settings

@app.get("/custom-info")
async def get_custom_info(settings = Depends(get_custom_settings)):
    return {"feature_flag": settings.FEATURE_FLAG_ENABLED}
```

### Environment-Specific Settings

The config module includes environment-specific settings classes. The environment is selected via the `APP_ENV` environment variable (see below):

```python
from fastcore.config import get_settings

# The environment is determined by the APP_ENV variable in your .env or environment
settings = get_settings()  # Will load Development, Production, or Testing settings
```

## Environment Variables

Common environment variables (see .env.example file in this module):

- Place each variable on a separate line in your `.env` file. Booleans should be `true`/`false` (unquoted), and strings quoted if they contain special characters.
- Some variables (like `ALEMBIC_DATABASE_URL`, `CACHE_KEY_PREFIX`) are optional and only needed for advanced use cases.

- `APP_NAME`: Name of your application
- `VERSION`: Application version
- `DEBUG`: Enable debug mode (default: `False` in production)
- `DATABASE_URL`: Database connection string (e.g., `postgresql+asyncpg://...`)
- `ALEMBIC_DATABASE_URL`: Sync DB connection for Alembic migrations (optional)
- `CACHE_URL`: Redis cache connection string (e.g., `redis://localhost:6379/0`)
- `CACHE_DEFAULT_TTL`: Default cache time-to-live (seconds)
- `CACHE_KEY_PREFIX`: Optional prefix for cache keys
- `JWT_SECRET_KEY`: Secret key for JWT token signing
- `JWT_ALGORITHM`: Algorithm for JWT (default: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiry (minutes)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiry (days)
- `JWT_AUDIENCE`: JWT audience claim
- `JWT_ISSUER`: JWT issuer claim
- `MIDDLEWARE_CORS_OPTIONS`: CORS options as JSON string (e.g., '{"allow_origins":["*"]}')
- `RATE_LIMITING_OPTIONS`: Rate limiting options as JSON string
- `RATE_LIMITING_BACKEND`: "memory" or "redis"
- `HEALTH_PATH`: Health check endpoint path
- `HEALTH_INCLUDE_DETAILS`: Include detailed health info (true/false)
- `METRICS_PATH`: Prometheus metrics endpoint path
- `METRICS_EXCLUDE_PATHS`: JSON list of paths to exclude from metrics
- `APP_ENV`: Set to `development`, `production`, or `testing` to select environment

> Note: The default `get_settings()` always returns the built-in environment-specific settings. To use your own settings class globally, pass it to the factory or use your own dependency injection function as shown above.

## Integration with Factory

The config module is automatically initialized when using `configure_app`:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Will load config from environment
```