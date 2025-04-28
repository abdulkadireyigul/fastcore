# FastCore

Core utilities and modules for building robust FastAPI applications with minimal boilerplate.

## Features

- **Configuration**: Environment-aware settings via Pydantic (`fastcore.config`)
- **Logging**: Structured or JSON logging setup (`fastcore.logging`)
- **Schemas**: Standardized API metadata and response models (`fastcore.schemas`)
- **Error Handling**: Consistent exceptions and handlers (`fastcore.errors`)
- **Caching**: Redis-based async cache with decorator support (`fastcore.cache`)
- **Database**: Async SQLAlchemy integration and repository pattern (`fastcore.db`)
- **Security**: JWT authentication, password hashing, and role-based access (`fastcore.security`)
- **Middleware**: CORS, rate limiting, and request timing (`fastcore.middleware`)
- **Monitoring**: Health checks, Prometheus metrics, and request IDs (`fastcore.monitoring`)
- **Factory**: Single-entrypoint app configuration (`fastcore.factory`)

## Installation

Install the package and required dependencies:

```bash
poetry add fastcore redis sqlalchemy asyncpg pydantic passlib[bcrypt] pyjwt prometheus_client
```

> If loading from source:
> ```bash
> git clone https://github.com/your-org/fastcore.git
> cd fastcore
> poetry install --all-extras
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

## Production Checklist

- [x] All tests passing (unit & integration)
- [x] Coverage > 60% (core logic covered)
- [x] Environment variables and secrets managed securely
- [x] Logging and monitoring configured for production
- [x] CORS, rate limiting, and security best practices enabled
- [x] Documentation and changelog up to date

## Testing

Run all tests and check coverage:

```bash
poetry run pytest --cov=src --cov-report=term-missing
```

## Module Documentation

Each submodule includes a detailed README in its folder:

- `src/config/README.md`
- `src/logging/README.md`
- `src/schemas/README.md`
- `src/errors/README.md`
- `src/cache/README.md`
- `src/db/README.md`
- `src/security/README.md`
- `src/middleware/README.md`
- `src/monitoring/README.md`
- `src/factory/README.md`

## Versioning

FastCore follows [Semantic Versioning](https://semver.org/) (SemVer):
- **MAJOR** version (x.0.0) - Incompatible API changes
- **MINOR** version (0.x.0) - Functionality added in a backward-compatible manner
- **PATCH** version (0.0.x) - Backward-compatible bug fixes

Current version: **0.1.0** (API v1)

### Version Compatibility

You can check the current version and API version in your code:

```python
import fastcore
print(fastcore.__version__)
print(fastcore.__api_version__)
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
