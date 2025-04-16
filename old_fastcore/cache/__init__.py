"""
FastCore Cache Module.

This module provides caching functionality for FastCore applications.
It includes various cache backends, a cache manager, and decorators
for easy application of caching to functions.

Basic usage:
    from fastcore.cache import cached, configure_cache
    
    # Configure a memory cache
    configure_cache(cache_type="memory", max_size=1000)
    
    @cached(ttl=60)  # Cache results for 60 seconds
    def expensive_calculation(x, y):
        # ... some expensive operation
        return result
"""

from .backends import CacheBackend, MemoryCache, NullCache, RedisCache
from .decorator import cached, invalidate_cache
from .manager import CacheManager, configure_cache, get_cache_manager

__all__ = [
    # Backends
    "CacheBackend",
    "MemoryCache",
    "NullCache",
    "RedisCache",
    # Decorator
    "cached",
    "invalidate_cache",
    # Manager
    "CacheManager",
    "configure_cache",
    "get_cache_manager",
]
