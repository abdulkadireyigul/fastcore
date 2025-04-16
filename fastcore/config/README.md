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

## Structure

- `base.py`: Base settings class
- `settings.py`: Settings factory and singleton instance
- `development.py`: Development environment settings
- `production.py`: Production environment settings
- `testing.py`: Testing environment settings