"""
FastCore cache module: public API

Features:
- Async Redis-based cache backend (RedisCache)
- Function-level async caching decorator
- FastAPI dependency for cache access
- Lifecycle management for FastAPI apps

Limitations:
- Only Redis backend is implemented (no in-memory or other backends)
- Only async functions are supported (no sync cache/decorator)
- No advanced Redis features (pub/sub, streams, etc.)
- No fallback if Redis is unavailable
"""
from fastcore.cache.backends import RedisCache
from fastcore.cache.base import BaseCache
from fastcore.cache.decorators import cache

# Do NOT re-export get_cache, setup_cache here to avoid import ambiguity

__all__ = [
    "BaseCache",
    "RedisCache",
    "cache",
]
