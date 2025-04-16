# Logging Module

A simple logging interface for FastAPI applications that integrates with the config module.

## Features

- Easy-to-use logger configuration
- Integration with application settings
- Standard log formatting
- Debug mode support
- JSON format support for structured logging

## Usage

### Basic Usage

```python
from fastcore_v2.logging import get_logger

# Create a logger for your module
logger = get_logger(__name__)

# Use standard logging methods
logger.info("Application started")
logger.debug("Debug information")
logger.error("An error occurred")
```

### With Application Settings

```python
from fastcore_v2.config import settings
from fastcore_v2.logging import get_logger

# Logger will respect settings.DEBUG
logger = get_logger(__name__, settings)

# Will only show if DEBUG=True
logger.debug("Debug message")
```

### JSON Format Logging

```python
from fastcore_v2.logging import get_logger

# Enable JSON format for structured logging
logger = get_logger(__name__, json_format=True)

logger.info("User logged in")
# Output: {"timestamp": "2025-04-14T10:30:00", "level": "INFO", "message": "User logged in"}
```

### Custom Logger with JsonFormatter

```python
import logging
from fastcore_v2.logging import JsonFormatter

# Create your own logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)

logger.info("Custom logger with JSON format")
```

### Custom Configuration

```python
from fastcore_v2.logging import setup_logger

# Configure a logger with custom settings
logger = setup_logger(
    name=__name__,
    level="DEBUG",
    format="%(asctime)s - %(levelname)s - %(message)s",
    json_format=True  # Enable JSON formatting
)
```

## Log Levels

The module supports standard Python logging levels:
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

## Structure

- `logger.py`: Core logging functionality
- `formatters.py`: Custom log formatters (JsonFormatter)
- `__init__.py`: Public API

## Integration with Config Module

The logging module integrates with the config module's debug settings:
- When `settings.DEBUG = True`, debug logs are enabled
- When `settings.DEBUG = False`, debug logs are suppressed