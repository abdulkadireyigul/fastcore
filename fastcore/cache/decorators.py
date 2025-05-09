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

    def normalize(obj):
        if obj is None:
            return ""
        if isinstance(obj, dict):
            if not obj:
                return ""
            return tuple(sorted((str(k), normalize(v)) for k, v in obj.items()))
        elif isinstance(obj, (list, tuple)):
            return tuple(normalize(x) for x in obj)
        else:
            return str(obj)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Retrieve cache instance
            cache_instance = await get_cache()

            # Construct cache key based on function and arguments
            key_data = {
                "func": f"{func.__module__}.{func.__name__}",
                "args": tuple(str(a) for a in args),
                "kwargs": tuple(
                    (str(k), normalize(v)) for k, v in sorted(kwargs.items())
                ),
            }
            key_str = json.dumps(key_data, sort_keys=True)
            key_hash = hashlib.sha256(key_str.encode()).hexdigest()
            full_key = f"{prefix or ''}{key_hash}"

            # Debug logging
            if hasattr(cache_instance, "_logger"):
                cache_instance._logger.debug(f"[cache] key_data: {key_data}")
                cache_instance._logger.debug(f"[cache] key_str: {key_str}")
                cache_instance._logger.debug(f"[cache] key_hash: {key_hash}")
                cache_instance._logger.debug(f"[cache] full_key: {full_key}")

            # Attempt to get cached value
            try:
                cached = await cache_instance.get(full_key)
            except Exception as e:
                cache_instance._logger.error(f"Cache get error: {e}") if hasattr(
                    cache_instance, "_logger"
                ) else None
                cached = None
            if cached is not None:
                return cached

            # Call the wrapped function and cache its result
            result = await func(*args, **kwargs)
            try:
                # Serialize Pydantic models or lists of models
                if hasattr(result, "model_dump_json"):
                    serializable = json.loads(result.model_dump_json())
                elif (
                    isinstance(result, list)
                    and result
                    and hasattr(result[0], "model_dump_json")
                ):
                    serializable = [
                        json.loads(item.model_dump_json()) for item in result
                    ]
                else:
                    serializable = result
                await cache_instance.set(full_key, serializable, ttl=ttl)
            except Exception as e:
                cache_instance._logger.error(f"Cache set error: {e}") if hasattr(
                    cache_instance, "_logger"
                ) else None
            return result

        return wrapper

    return decorator
