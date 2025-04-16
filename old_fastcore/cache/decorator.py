"""
Cache decorator for easy function result caching.

This module provides the @cached decorator which can be used to
automatically cache function results. It also provides utility
functions for working with cached functions.
"""

import functools
import inspect
import pickle
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast

from fastcore.logging import get_logger

from .manager import get_cache_manager

logger = get_logger(__name__)

# Type variable for generic function
F = TypeVar("F", bound=Callable[..., Any])


def _generate_cache_key(
    func: Callable,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    namespace: Optional[str] = None,
    key_prefix: Optional[str] = None,
    skip_args: Optional[List[int]] = None,
    skip_kwargs: Optional[List[str]] = None,
) -> str:
    """
    Generate a cache key for a function call.

    Args:
        func: The function being called
        args: Positional arguments to the function
        kwargs: Keyword arguments to the function
        namespace: Optional namespace to prefix the key with
        key_prefix: Optional prefix for the key
        skip_args: Optional list of argument indices to exclude from key generation
        skip_kwargs: Optional list of keyword argument names to exclude from key generation

    Returns:
        A string key uniquely identifying this function call
    """
    # Get function's module and name
    module_name = func.__module__
    func_name = func.__qualname__

    # Start with the function's identity
    base_key = f"{module_name}.{func_name}"

    # Add namespace if provided
    if namespace:
        base_key = f"{namespace}:{base_key}"

    # Add key_prefix if provided
    if key_prefix:
        base_key = f"{key_prefix}:{base_key}"

    # Filter args and kwargs if needed
    filtered_args = list(args)
    if skip_args:
        for idx in sorted(skip_args, reverse=True):
            if idx < len(filtered_args):
                filtered_args[idx] = None

    filtered_kwargs = kwargs.copy()
    if skip_kwargs:
        for key in skip_kwargs:
            if key in filtered_kwargs:
                filtered_kwargs[key] = None

    # Create a unique key based on the function and arguments
    try:
        # Try to use pickle for a compact representation
        # This might fail for objects that can't be pickled
        args_kwargs_str = pickle.dumps((tuple(filtered_args), filtered_kwargs))
        arg_hash = hash(args_kwargs_str)
        key = f"{base_key}:{arg_hash}"
    except Exception:
        # Fall back to string representation for non-picklable objects
        args_str = str(filtered_args)
        kwargs_str = str(sorted(filtered_kwargs.items()))
        key = f"{base_key}:{hash(args_str + kwargs_str)}"

    return key


def cached(
    ttl: Optional[int] = None,
    namespace: Optional[str] = None,
    key_prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None,
    cache_name: str = "default",
    skip_args: Optional[List[int]] = None,
    skip_kwargs: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live for cached values in seconds (None for no expiration)
        namespace: Namespace for cache keys
        key_prefix: Prefix for cache keys
        key_builder: Optional custom function for generating cache keys
        cache_name: Name of the cache backend to use
        skip_args: List of positional argument indices to exclude from key generation
        skip_kwargs: List of keyword argument names to exclude from key generation

    Returns:
        Decorated function that uses caching

    Example:
        >>> @cached(ttl=60)
        >>> def expensive_function(x, y):
        >>>     # Expensive computation here
        >>>     return x + y
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_manager = get_cache_manager()

            # Generate cache key
            if key_builder:
                key = key_builder(func, *args, **kwargs)
            else:
                key = _generate_cache_key(
                    func,
                    args,
                    kwargs,
                    namespace=namespace,
                    key_prefix=key_prefix,
                    skip_args=skip_args,
                    skip_kwargs=skip_kwargs,
                )

            # Try to get from cache
            hit, value = cache_manager.get_with_info(key, cache_name=cache_name)

            if hit:
                logger.debug(f"Cache hit for {func.__name__}")
                return value

            # Cache miss, call the function
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)

            # Store in cache
            cache_manager.set(key, result, ttl=ttl, cache_name=cache_name)

            return result

        # Add method to invalidate cache for specific arguments
        def invalidate(*args: Any, **kwargs: Any) -> bool:
            """Invalidate the cache for specific arguments."""
            cache_manager = get_cache_manager()

            key = (
                _generate_cache_key(
                    func,
                    args,
                    kwargs,
                    namespace=namespace,
                    key_prefix=key_prefix,
                    skip_args=skip_args,
                    skip_kwargs=skip_kwargs,
                )
                if not key_builder
                else key_builder(func, *args, **kwargs)
            )

            return cache_manager.delete(key, cache_name=cache_name)

        wrapper.invalidate = invalidate  # type: ignore

        return cast(F, wrapper)

    return decorator


def invalidate_cache(func: Callable, *args: Any, **kwargs: Any) -> bool:
    """
    Invalidate the cache for a specific function call.

    This is useful for functions that have been decorated with @cached,
    but can also be used for functions that haven't been decorated
    (if you know the key generation logic).

    Args:
        func: The function whose cache to invalidate
        *args: The arguments that were passed to the function
        **kwargs: The keyword arguments that were passed to the function

    Returns:
        True if the cache was invalidated, False otherwise

    Example:
        >>> @cached()
        >>> def my_func(x, y):
        >>>     return x + y
        >>>
        >>> # Call the function (result will be cached)
        >>> result = my_func(1, 2)
        >>>
        >>> # Invalidate the cache for those specific arguments
        >>> invalidate_cache(my_func, 1, 2)
    """
    # Check if the function has an invalidate method (added by @cached)
    if hasattr(func, "invalidate") and callable(func.invalidate):
        return func.invalidate(*args, **kwargs)  # type: ignore

    # Function wasn't decorated, try to invalidate manually
    cache_manager = get_cache_manager()

    # Generate a key as the decorator would
    key = _generate_cache_key(func, args, kwargs)

    # Try to delete from cache
    return cache_manager.delete(key)
