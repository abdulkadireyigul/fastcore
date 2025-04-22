"""
FastCore cache module: public API
"""
from src.cache.backends import RedisCache
from src.cache.base import BaseCache
from src.cache.decorators import cache
from src.cache.manager import get_cache, setup_cache

__all__ = [
    "BaseCache",
    "RedisCache",
    "get_cache",
    "setup_cache",
    "cache",
]
