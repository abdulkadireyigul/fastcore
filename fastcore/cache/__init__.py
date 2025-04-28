"""
FastCore cache module: public API
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
