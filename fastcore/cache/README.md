# Cache Module

A Redis-based cache module for FastAPI applications, providing simple cache operations, lifecycle management, and decorator support.

## Features

- Redis backend implemented with `aioredis`
- Configuration via `BaseAppSettings`: `CACHE_URL`, `CACHE_DEFAULT_TTL`, `CACHE_KEY_PREFIX`
- Automatic initialization and shutdown on FastAPI app startup/shutdown
- FastAPI dependency: `get_cache()` for accessing the cache instance
- Async decorator `@cache(ttl, prefix)` for function-level caching

## Installation

Install the Redis client:

```bash
poetry add redis
```

## Configuration

Configure cache settings via environment variables or programmatically in your settings class:

```env
CACHE_URL=redis://localhost:6379/0
CACHE_DEFAULT_TTL=300
CACHE_KEY_PREFIX=myapp:
```

Fields on `BaseAppSettings`:

- `CACHE_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `CACHE_DEFAULT_TTL`: Default time-to-live in seconds (default: `300`)
- `CACHE_KEY_PREFIX`: Optional prefix for all cache keys

## Usage

### Factory Integration

In your application factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)
```

This will automatically register the cache lifecycle handlers.

### Dependency Injection

Use the `get_cache` dependency to access cache operations:

```python
from fastapi import APIRouter, Depends
from fastcore.cache import get_cache

router = APIRouter()

@router.get("/count")
async def get_count(cache = Depends(get_cache)):
    value = await cache.get("counter") or 0
    return {"counter": int(value)}
```

### Decorator

Apply the `cache` decorator to any async function to enable caching:

```python
from fastcore.cache import cache as cache_decorator

@cache_decorator(ttl=60, prefix="users:")
async def fetch_user(user_id: str) -> dict:
    # Expensive operation (e.g., DB call)
    return {"id": user_id, "name": "User"}
```

The decorator will generate a key based on function name and arguments, retrieve cached results, or store new ones with the specified TTL.

## Limitations

- Only Redis backend is implemented (no in-memory or other backends)
- Only async functions are supported (no sync cache/decorator)
- No fallback if Redis is unavailable
- No advanced Redis features (pub/sub, streams, etc.)
- No distributed locking or rate limiting at the cache layer

## Error Handling

Cache-related errors are logged using the global logger and will raise exceptions if Redis is unreachable. Handle exceptions as needed in your application.
