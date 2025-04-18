import functools
import hashlib
import json
from typing import Any, Callable, Optional

from fastcore.cache.manager import get_cache


def cache(
    ttl: Optional[int] = None, prefix: Optional[str] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for caching async function results.

    Args:
        ttl: Optional time-to-live for this cache entry (seconds)
        prefix: Optional key prefix to namespace cache keys
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Retrieve cache instance
            cache_instance = await get_cache()

            # Construct cache key based on function and arguments
            key_data = {
                "func": f"{func.__module__}.{func.__name__}",
                "args": args,
                "kwargs": kwargs,
            }
            key_str = json.dumps(key_data, default=str, sort_keys=True)
            key_hash = hashlib.sha256(key_str.encode()).hexdigest()
            full_key = f"{prefix or ''}{key_hash}"

            # Attempt to get cached value
            cached = await cache_instance.get(full_key)
            if cached is not None:
                return cached

            # Call the wrapped function and cache its result
            result = await func(*args, **kwargs)
            await cache_instance.set(full_key, result, ttl=ttl)
            return result

        return wrapper

    return decorator
