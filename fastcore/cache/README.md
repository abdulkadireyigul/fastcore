# Cache Module

A high-performance, Redis-based cache module for FastAPI applications. It features a fail-silent architecture, `orjson` optimization, and a raw performance mode for extreme concurrency.

## Features

- **High Performance:** Built on `redis-py` (async) and optimized with `orjson` for ultra-fast serialization.
- **Fail-Silent:** Designed to be resilient. If Redis goes down, your application keeps working (logs errors and acts as a cache miss).
- **Raw Mode:** Optional `return_raw=True` parameter to skip Pydantic validation on cache hits, delivering **300x+ speedups**.
- **Atomic Operations:** Supports atomic increment-with-expire via Lua scripts to prevent race conditions.
- **Lifecycle Management:** Automatic startup/shutdown handling via `setup_cache`.

## Installation

Install the package and required dependencies:

```bash
poetry add redis orjson
```

> **Note:** `orjson` is highly recommended for performance, but the module will fallback to standard `json` if it's not installed.

## Usage

### 1. Setup

Configure the cache in your application startup (e.g., in `main.py` or factory). This initializes the connection and registers shutdown handlers.

```python
from fastapi import FastAPI
from fastcore.cache import setup_cache
from fastcore.config import settings # Your BaseAppSettings

app = FastAPI()

# Registers startup/shutdown handlers
setup_cache(app, settings)
```

### 2. Dependency Injection

Use `get_cache` to access the low-level backend for operations like `get`, `set`, `delete`, `clear`, or `incr`.

```python
from fastapi import APIRouter, Depends
from fastcore.cache import get_cache, BaseCache

router = APIRouter()

@router.get("/stats")
async def get_stats(cache: BaseCache = Depends(get_cache)):
    # Atomic increment
    await cache.incr("visitors")

    # Retrieve value
    count = await cache.get("visitors")
    return {"count": count}
```

### 3. Decorator (The Power Move)

The `@cache` decorator handles key generation, serialization, and TTL automatically. It supports two modes:

#### Standard Mode (Safe & Typed)

Best for critical data where type validation and data integrity are essential.

```python
from fastcore.cache import cache
from myapp.models import UserProfile

@cache(ttl=60, prefix="user:")
async def get_user_profile(user_id: str) -> UserProfile:
    # Returns a Pydantic model
    # Cache Hit: Deserializes & Validates data (Safe)
    return await db.users.get(user_id)
```

#### 🚀 Raw Mode (Extreme Performance)

Best for high-traffic lists, feeds, or read-heavy endpoints where data schema is trusted. This skips the CPU-intensive Pydantic validation step on cache hits.

```python
from typing import List
from myapp.models import NewsItem

@cache(ttl=300, return_raw=True)
async def get_news_feed() -> List[NewsItem]:
    # Cache Hit: Returns raw List[dict] directly from Redis
    # Skips Pydantic validation overhead (300x faster)
    return await db.news.get_all()
```

## Performance Benchmarks

We compared the two modes using a dataset of **10,000 complex objects**:

| Scenario       | Mode     | Time per Call | Speedup    | Notes                             |
| -------------- | -------- | ------------- | ---------- | --------------------------------- |
| **Cache Hit**  | Standard | \~10.83 ms    | 1x         | Includes Pydantic validation      |
| **Cache Hit**  | **Raw**  | **\~0.03 ms** | **\~360x** | **Zero-copy, serialization only** |
| **Cache Miss** | Both     | \~9.50 ms     | -          | Fetch + Serialize + Write         |

_As seen above, utilizing `return_raw=True` eliminates 99% of the CPU overhead during cache hits._

## Configuration

Configure via environment variables (handled by `BaseAppSettings`):

```env
CACHE_URL=redis://localhost:6379/0
CACHE_DEFAULT_TTL=300
CACHE_KEY_PREFIX=myapp:
```

| Variable            | Default                    | Description                     |
| ------------------- | -------------------------- | ------------------------------- |
| `CACHE_URL`         | `redis://localhost:6379/0` | Redis connection string         |
| `CACHE_DEFAULT_TTL` | `300`                      | Default time-to-live in seconds |
| `CACHE_KEY_PREFIX`  | `""`                       | Optional prefix for all keys    |

## Error Handling

The module adopts a **Fail-Silent** philosophy to ensure high availability:

- **Redis Connection Error:** Logged as error, treated as Cache Miss (application continues working).
- **Serialization Error:** Logged as error, cache operation skipped.
- **Initialization Error:** App starts, but cache operations will log errors until connection is restored.

This ensures your application remains available even if the cache layer is temporarily unstable.
