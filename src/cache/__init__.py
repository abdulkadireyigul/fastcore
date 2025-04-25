"""
FastCore cache module: public API
"""
from src.cache.backends import RedisCache
from src.cache.base import BaseCache
from src.cache.decorators import cache

# Do NOT re-export get_cache, setup_cache here to avoid import ambiguity

__all__ = [
    "BaseCache",
    "RedisCache",
    "cache",
]
