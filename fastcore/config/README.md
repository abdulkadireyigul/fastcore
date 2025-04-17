# Config Module

A simple, environment-aware configuration system for FastAPI applications.

## Features

- Environment-based configuration management
- Support for .env files
- Type-safe settings with Pydantic
- Pre-configured environments (development, testing, production)

## Usage

### Basic Usage

```python
from fastcore.config import settings

# Access settings directly
app_name = settings.APP_NAME
debug_mode = settings.DEBUG
```

### Environment-Specific Settings

The module automatically loads the correct settings based on the `APP_ENV` environment variable:

```python
# Set environment variable
# export APP_ENV=production  # Linux/Mac
# set APP_ENV=production    # Windows

from fastcore.config import settings

# Will use ProductionSettings
print(settings.DEBUG)  # False
```

### Custom Settings

You can create your own settings by inheriting from BaseAppSettings:

```python
from fastcore.config import BaseAppSettings

class MyCustomSettings(BaseAppSettings):
    CUSTOM_FIELD: str = "default value"
    API_KEY: str
```

## Environment Variables

The following environment variables are supported:

- `APP_ENV`: Determines which settings to load (development, testing, production)
- `APP_NAME`: Override the application name
- `DEBUG`: Override debug mode
- `VERSION`: Override version number
- `CACHE_URL`: Redis connection URL for caching (e.g., `redis://localhost:6379/0`)
- `CACHE_DEFAULT_TTL`: Default TTL in seconds for cache entries (e.g., `300`)
- `CACHE_KEY_PREFIX`: Optional prefix for cache keys (e.g., `myapp:`)
- `DATABASE_URL`: Database connection URL (e.g., `postgresql+asyncpg://user:pass@host:port/dbname`)
- `DB_ECHO`: Enable SQL query logging (e.g., `true` or `false`)
- `DB_POOL_SIZE`: Database connection pool size (e.g., `5`)

## Structure

- `base.py`: Base settings class
- `settings.py`: Settings factory and singleton instance
- `development.py`: Development environment settings
- `production.py`: Production environment settings
- `testing.py`: Testing environment settings