# Logging Module

A structured logging system for FastAPI applications that supports both text and JSON formats.

## Features

- Simple configuration through application settings
- JSON formatting support for structured logging
- Debug mode detection from settings
- Logger dependency pattern for consistent logging across modules
- Compatible with standard Python logging

## Limitations

- Only console (stdout) logging is supported out of the box.
- No file logging, log rotation, or external service integration.
- JSON logs include only timestamp, level, and message by default. Extra fields passed with `extra=` are not included unless you extend the formatter.

## Installation

Install the logging dependencies:

```bash
poetry add fastapi
```

## Usage

### Basic Usage

Get a logger instance for your module:

```python
from fastcore.logging import get_logger
from fastcore.config import get_settings

# Get settings (or they can be passed as parameter)
settings = get_settings()

# Create a logger for the current module
logger = get_logger(__name__, settings)

# Log at different levels
logger.debug("Debug message with detail info", extra={"request_id": "123"})
logger.info("Operation completed successfully")
logger.warning("Something unusual happened")
logger.error("An error occurred", exc_info=True)
logger.critical("System cannot continue")
```

### As a Dependency

You can use the logging module in FastAPI dependency injection:

```python
from fastapi import APIRouter, Depends
from fastcore.logging import get_logger
from fastcore.config import get_settings

router = APIRouter()
settings = get_settings()

def get_request_logger():
    return get_logger("api.request", settings)

@router.get("/items/{item_id}")
async def get_item(item_id: str, logger = Depends(get_request_logger)):
    logger.info(f"Processing request for item {item_id}")
    # ...processing...
    return {"id": item_id, "name": "Test Item"}
```

### Ensuring a Logger Exists

The `ensure_logger` utility provides a consistent pattern for modules that may receive a logger or need to create one:

```python
from fastcore.logging import ensure_logger, Logger
from typing import Optional

def process_data(data: dict, logger: Optional[Logger] = None):
    # Get or create a logger
    log = ensure_logger(logger, __name__)
    
    log.info("Processing data started")
    # ...processing logic...
    log.info("Processing completed")
```

### JSON Formatting

Enable JSON logging for structured output:

```python
from fastcore.logging import get_logger

# Enable JSON formatting
logger = get_logger(__name__, json_format=True)

# Log with structured data
logger.info(
    "User logged in", 
    extra={
        "user_id": "12345",
        "ip_address": "192.168.1.1",
        "session_id": "abc123"
    }
)
```

## Configuration

Configure logging through environment variables or settings:

```python
from fastcore.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = False
```

Common environment variables:
- `LOG_LEVEL`: Sets the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_JSON_FORMAT`: Enables JSON-formatted logs when set to "true"

## Integration with Factory

Logging is automatically set up when using the application factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Sets up logging based on app settings
```