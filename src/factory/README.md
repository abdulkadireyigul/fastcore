# Factory Module

Provides a single-entrypoint to configure a FastAPI application with all FastCore core modules.

## Usage

In your FastAPI application:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
# Automatically sets up config, logging, errors, cache, and database
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

The factory module ties together:

- **Configuration** (`fastcore.config`)
- **Logging** (`fastcore.logging`)
- **Error handling** (`fastcore.errors`)
- **Cache** (`fastcore.cache`)
- **Database** (`fastcore.db`)

## Extension

If you need to customize the setup order or add additional initialization steps, call the core setup functions individually:

```python
from fastapi import FastAPI
from fastcore.config import settings
from fastcore.logging import get_logger
from fastcore.errors import setup_errors
from fastcore.cache import setup_cache
from fastcore.db import setup_db

app = FastAPI()
app_settings = settings
logger = get_logger(__name__, app_settings)
setup_errors(app, app_settings, logger)
setup_cache(app, app_settings, logger)
setup_db(app, app_settings, logger)
```
