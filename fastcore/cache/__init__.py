"""
FastCore cache module: public API
"""
from fastcore.cache.backends import RedisCache
from fastcore.cache.base import BaseCache
from fastcore.cache.decorators import cache
from fastcore.cache.manager import get_cache, setup_cache

__all__ = [
    "BaseCache",
    "RedisCache",
    "get_cache",
    "setup_cache",
    "cache",
]
