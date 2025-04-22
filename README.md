# FastCore

Core utilities and modules for building robust FastAPI applications with minimal boilerplate.

## Features

- **Configuration**: Environment-aware settings via Pydantic (`fastcore.config`)
- **Logging**: Structured or JSON logging setup (`fastcore.logging`)
- **Schemas**: Standardized API metadata and response models (`fastcore.schemas`)
- **Error Handling**: Consistent exceptions and handlers (`fastcore.errors`)
- **Caching**: Redis-based async cache with decorator support (`fastcore.cache`)
- **Factory**: Single-entrypoint app configuration (`fastcore.factory`)

## Installation

Install the package and required dependencies:

```bash
pip install fastcore aioredis
```

> If loading from source:
> ```bash
> git clone https://github.com/your-org/fastcore.git
> cd fastcore
> pip install .[all]
> ```

## Quick Start

```python
from fastapi import FastAPI, Depends
from fastcore.factory import configure_app
from fastcore.cache import get_cache, cache as cache_decorator

app = FastAPI()
# Configure all core modules
configure_app(app)

# Dependency-based cache usage
@app.get("/counter")
async def read_counter(cache=Depends(get_cache)):
    count = await cache.get("counter") or 0
    await cache.set("counter", int(count) + 1)
    return {"counter": int(count) + 1}

# Function-level caching
@cache_decorator(ttl=60, prefix="users:")
async def fetch_user(user_id: str) -> dict:
    # simulate I/O
    return {"id": user_id, "name": "Example"}
```

## Module Documentation

Each submodule includes a detailed README in its folder:

- `fastcore/config/README.md`
- `fastcore/logging/README.md`
- `fastcore/schemas/README.md`
- `fastcore/errors/README.md`
- `fastcore/cache/README.md`
- `fastcore/db/README.md`
- `fastcore/security/README.md`
- `fastcore/middleware/README.md`
- `fastcore/factory/README.md`

## Versioning

FastCore follows [Semantic Versioning](https://semver.org/) (SemVer) for version numbering:

- **MAJOR** version (x.0.0) - Incompatible API changes
- **MINOR** version (0.x.0) - Functionality added in a backward-compatible manner
- **PATCH** version (0.0.x) - Backward-compatible bug fixes

Current version: **0.1.0** (API v1)

### Version Compatibility

You can check the current version and API version in your code:

```python
import fastcore

print(fastcore.__version__)  # Package version, e.g., "0.1.0"
print(fastcore.__api_version__)  # API version, e.g., "v1"
```

### Breaking Changes

Breaking changes are documented in the [CHANGELOG.md](CHANGELOG.md) file. As this is a pre-1.0 library:

- **0.x** releases may contain breaking changes as the API evolves
- Once we reach **1.0.0**, breaking changes will only occur in major version bumps

### Minimum Requirements

- Python: 3.8+
- FastAPI: 0.100.0+

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/...`)
3. Commit your changes (`git commit -m "..."`)
4. Push to the branch (`git push origin feature/...`)
5. Open a pull request

## License

MIT License. See [LICENSE](LICENSE) for details.
