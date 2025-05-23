# Factory Module

Provides a single-entrypoint to configure a FastAPI application with all FastCore core modules.

## Installation

Install FastCore (factory auto-includes all dependencies):

```bash
poetry add fastcore
```

## Usage

In your FastAPI application:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
# Automatically sets up config, logging, errors, cache, database, security, middleware, and monitoring
configure_app(app)
```

Optionally, you can pass a custom settings object to `configure_app`:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app
from fastcore.config import BaseAppSettings

class CustomSettings(BaseAppSettings):
    CUSTOM_FLAG: bool = True

app = FastAPI()
configure_app(app, settings=CustomSettings())
```

## Modules Included

The factory module ties together:

- **Configuration** (`fastcore.config`)
- **Logging** (`fastcore.logging`)
- **Error handling** (`fastcore.errors`)
- **Cache** (`fastcore.cache`)
- **Database** (`fastcore.db`)
- **Security** (`fastcore.security`)
- **Middleware** (`fastcore.middleware`)
- **Monitoring** (`fastcore.monitoring`)

## Extension

If you need to customize the setup order or add additional initialization steps, call the core setup functions individually:

```python
from fastapi import FastAPI
from fastcore.config import settings
from fastcore.logging import get_logger
from fastcore.errors import setup_errors
from fastcore.cache import setup_cache
from fastcore.db import setup_db
from fastcore.security import setup_security
from fastcore.middleware import setup_middlewares
from fastcore.monitoring import setup_monitoring

app = FastAPI()
app_settings = settings
logger = get_logger(__name__, app_settings)
setup_errors(app, app_settings, logger)
setup_cache(app, app_settings, logger)
setup_db(app, app_settings, logger)
setup_security(app, app_settings, logger)
setup_middlewares(app, app_settings, logger)
setup_monitoring(app, app_settings, logger)
```

## Limitations

- Only full setup is supported by default; partial setup requires manual calls to individual setup functions
- No hooks for custom setup steps or post-configuration logic
- Designed for a single FastAPI app instance at a time
- No support for dynamic reconfiguration or hot-reloading of modules at runtime
