# FastCore

FastCore is a collection of core utilities and components for FastAPI applications, designed to eliminate duplication and inconsistency across projects.

## Features

- Configuration management with environment support
- Database integration utilities
- Common API utilities (pagination, sorting, etc.)
- Security components
- Caching mechanisms
- Error handling
- Internationalization (i18n)
- Monitoring tools

## Installation

### For Users

Install the library directly from your git repository or PyPI:

```bash
# From git
pip install git+https://github.com/abdulkadireyigul/fastcore.git

# If published on PyPI
pip install fastcore

# With database extras
pip install "fastcore[db]"
```

### For Developers

This project uses Poetry for dependency management. To set up a development environment:

1. Install Poetry (if you haven't already):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone the repository and install dependencies:
```bash
git clone https://github.com/abdulkadireyigul/fastcore.git
cd fastcore
poetry install --with dev
```

3. Activate the virtual environment:
```bash
poetry shell
```

## Usage

### Configuration Management

```python
from fastapi import FastAPI, Depends
from fastcore.config import AppSettings, Environment

# Load settings
settings = AppSettings.load(Environment.DEVELOPMENT)

# Create FastAPI app
app = FastAPI(
    title=settings.API.TITLE,
    description=settings.API.DESCRIPTION,
    version=settings.API.VERSION,
)

# Create a dependency
def get_settings():
    return settings

# Use in an endpoint
@app.get("/info")
async def get_info(settings: AppSettings = Depends(get_settings)):
    return {
        "app_name": settings.API.TITLE,
        "environment": settings.ENV
    }
```

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Quality

```bash
# Format code
poetry run black fastcore
poetry run isort fastcore

# Type checking
poetry run mypy fastcore

# Run tests with coverage
poetry run pytest --cov=fastcore
```

### Building the Package

```bash
poetry build
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
