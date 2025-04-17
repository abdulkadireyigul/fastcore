"""
FastCore cache module: public API
"""
from .backends import RedisCache
from .base import BaseCache
from .decorators import cache
from .manager import get_cache, setup_cache

__all__ = [
    "BaseCache",
    "RedisCache",
    "get_cache",
    "setup_cache",
    "cache",
]
