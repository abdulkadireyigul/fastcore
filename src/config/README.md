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

### Environment-Specific Settings

The config module includes environment-specific settings classes:

```python
from fastcore.config import get_settings
from fastcore.config.base import Environment

# Force specific environment
settings = get_settings(env=Environment.DEVELOPMENT)
```

## Environment Variables

Common environment variables:

- `APP_NAME`: Name of your application
- `VERSION`: Application version
- `DEBUG`: Enable debug mode (default: `False` in production)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `DB_URL`: Database connection string
- `CACHE_URL`: Redis cache connection string
- `SECRET_KEY`: Secret key for token signing
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated)

## Integration with Factory

The config module is automatically initialized when using `configure_app`:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Will load config from environment
```