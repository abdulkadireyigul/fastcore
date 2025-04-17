import json
import logging
from typing import Any, Optional

import aioredis  # type: ignore

from .base import BaseCache


class RedisCache(BaseCache):
    """
    Redis-based cache backend implementation.
    """

    def __init__(
        self,
        url: str,
        default_ttl: int,
        prefix: str = "",
        logger: Optional[logging.Logger] = None,
    ):
        self._url = url
        self._default_ttl = default_ttl
        self._prefix = prefix
        self._logger = logger or logging.getLogger(__name__)
        self._redis: Optional[aioredis.Redis] = None

    async def init(self) -> None:
        """Initialize Redis connection and verify with ping."""
        self._redis = aioredis.from_url(
            self._url, encoding="utf-8", decode_responses=True
        )
        await self._redis.ping()

    async def get(self, key: str) -> Optional[Any]:
        full_key = f"{self._prefix}{key}"
        try:
            result = await self._redis.get(full_key)
            if result is None:
                self._logger.debug(f"Cache miss for key: {full_key}")
                return None
            # Attempt to deserialize JSON value
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                self._logger.debug("Returning raw cache value (non-JSON)")
                return result
        except Exception as e:
            self._logger.error(f"Cache get error for key {full_key}: {e}")
            raise

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        full_key = f"{self._prefix}{key}"
        expire = ttl if ttl is not None else self._default_ttl
        try:
            # Serialize non-string values to JSON
            store_value = json.dumps(value) if not isinstance(value, str) else value
            await self._redis.set(full_key, store_value, ex=expire)
            self._logger.debug(f"Cache set for key: {full_key} (ttl={expire})")
        except Exception as e:
            self._logger.error(f"Cache set error for key {full_key}: {e}")
            raise

    async def delete(self, key: str) -> None:
        full_key = f"{self._prefix}{key}"
        try:
            await self._redis.delete(full_key)
            self._logger.debug(f"Cache delete for key: {full_key}")
        except Exception as e:
            self._logger.error(f"Cache delete error for key {full_key}: {e}")
            raise

    async def clear(self, prefix: Optional[str] = None) -> None:
        pat = f"{self._prefix}{prefix or ''}*"
        try:
            # Use SCAN to avoid blocking Redis for large keyspaces
            async for key in self._redis.scan_iter(match=pat):
                await self._redis.delete(key)
            self._logger.debug(f"Cache clear using SCAN for pattern: {pat}")
        except Exception as e:
            self._logger.error(f"Cache clear error for pattern {pat}: {e}")
            raise

    async def close(self) -> None:
        """Close the Redis connection."""
        try:
            self._redis.close()
            await self._redis.wait_closed()
            self._logger.debug("Redis connection closed")
        except Exception as e:
            self._logger.error(f"Cache close error: {e}")
            raise
