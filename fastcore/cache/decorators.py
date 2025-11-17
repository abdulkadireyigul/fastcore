import functools
import hashlib
import inspect
import logging
from typing import Any, Callable, List, Optional, Type, get_type_hints

import orjson

from fastcore.cache.manager import get_cache


def _normalize(obj: Any) -> Any:
    """
    Convert arguments into a deterministic, hashable format.
    Recursive handling ensures that nested dicts/lists generate the same
    structure regardless of item order (for dicts).
    """
    if obj is None:
        return ""
    if isinstance(obj, dict):
        if not obj:
            return ""
        # Sort dict keys to ensure {a:1, b:2} and {b:2, a:1} produce the same hash
        return tuple(sorted((str(k), _normalize(v)) for k, v in obj.items()))
    elif isinstance(obj, (list, tuple)):
        return tuple(_normalize(x) for x in obj)
    else:
        # Convert custom objects to string representation
        return str(obj)


def _make_key(func: Callable, args: tuple, kwargs: dict, prefix: str = "") -> str:
    """
    Generate a unique, deterministic cache key based on the function signature
    and provided arguments.
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Skip 'self' or 'cls' arguments for instance/class methods to keep keys clean
    is_method = params and params[0].name in ("self", "cls")
    used_args = args[1:] if is_method else args

    key_data = {
        "func": f"{func.__module__}.{func.__name__}",
        "args": tuple(str(a) for a in used_args),
        "kwargs": tuple((str(k), _normalize(v)) for k, v in sorted(kwargs.items())),
    }

    # Since orjson is mandatory, this always returns bytes.
    # We use OPT_SORT_KEYS to ensure deterministic output for dictionaries.
    key_bytes: bytes = orjson.dumps(key_data, option=orjson.OPT_SORT_KEYS)

    # hashlib.sha256 accepts bytes, so Pylance is satisfied.
    key_hash = hashlib.sha256(key_bytes).hexdigest()
    return f"{prefix}{key_hash}"


def cache(
    ttl: Optional[int] = None, prefix: Optional[str] = None, return_raw: bool = False
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Async decorator for caching function results in Redis.

    Args:
        ttl: Time-To-Live in seconds. If None, uses the default backend TTL.
        prefix: Optional string prefix for the cache key.
        return_raw: If True, skips Pydantic validation on cache hits and returns
                    the raw dict/list from Redis (Performance Mode).
                    If False (default), attempts to re-validate data into Pydantic models.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Analyze return type to handle Pydantic models correctly
        model_type: Optional[Type[Any]] = None
        is_list = False

        try:
            # Use get_type_hints to resolve string forward references (e.g. "User")
            type_hints = get_type_hints(func)
            return_type = type_hints.get("return")

            if return_type:
                # Check for List[Model]
                origin = getattr(return_type, "__origin__", None)
                if origin in (list, List):
                    # Extract the inner type from List[Type]
                    args = getattr(return_type, "__args__", [])
                    if args and hasattr(args[0], "model_validate"):
                        model_type = args[0]
                        is_list = True
                # Check for Single Model
                elif hasattr(return_type, "model_validate"):
                    model_type = return_type
        except Exception:
            # If type resolution fails, proceed without automatic Pydantic validation
            pass

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 1. Retrieve Cache Instance
            try:
                cache_instance = await get_cache()
            except RuntimeError:
                # Fallback: If cache is not initialized, execute function directly
                return await func(*args, **kwargs)

            # 2. Generate Cache Key
            full_key = _make_key(func, args, kwargs, prefix or "")

            # 3. Read from Cache (GET)
            try:
                cached = await cache_instance.get(full_key)
            except Exception as e:
                # Fail-Silent: Log error and proceed as cache miss
                logger = getattr(cache_instance, "_logger", None)
                if isinstance(logger, logging.Logger):
                    logger.error(f"Cache get error: {e}")
                cached = None

            if cached is not None:
                # --- RAW MODE (High Performance) ---
                if return_raw:
                    return cached

                # --- COMPATIBILITY MODE (Pydantic Validation) ---
                if model_type:
                    try:
                        if is_list and isinstance(cached, list):
                            return [model_type.model_validate(item) for item in cached]
                        elif not is_list:
                            return model_type.model_validate(cached)
                    except Exception:
                        # If validation fails (data schema changed), treat as cache miss
                        pass

                return cached

            # 4. Cache Miss - Execute Function
            result = await func(*args, **kwargs)

            # 5. Write to Cache (SET)
            try:
                to_cache = result
                # Serialize Pydantic models to dicts before storage
                if hasattr(result, "model_dump"):
                    # Pydantic v2
                    to_cache = result.model_dump(mode="json")
                elif (
                    isinstance(result, list)
                    and result
                    and hasattr(result[0], "model_dump")
                ):
                    to_cache = [item.model_dump(mode="json") for item in result]

                # Backend handles serialization (orjson)
                await cache_instance.set(full_key, to_cache, ttl=ttl)
            except Exception as e:
                # Fail-Silent: Log error but do not raise exception
                logger = getattr(cache_instance, "_logger", None)
                if isinstance(logger, logging.Logger):
                    logger.error(f"Cache set error: {e}")

            return result

        return wrapper

    return decorator
