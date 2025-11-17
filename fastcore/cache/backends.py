import logging
from typing import Any, List, Optional

import orjson
from redis import asyncio as aredis  # type: ignore
from redis.exceptions import NoScriptError

from fastcore.cache.base import BaseCache
from fastcore.logging.manager import ensure_logger


class RedisCache(BaseCache):
    """
    Redis-based cache backend implementation using aioredis.

    Features:
    - Automatic serialization/deserialization using orjson (high performance).
    - Fail-silent operation (logs errors instead of raising exceptions).
    - Atomic increment operations with expiration support via Lua scripts.
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
        self._logger: logging.Logger = ensure_logger(logger, __name__)  # type: ignore
        self._redis: Optional[aredis.Redis] = None
        self._incr_script_sha: Optional[str] = None

    async def init(self) -> None:
        """Initialize Redis connection and verify connectivity."""
        # decode_responses=False ensures we handle raw bytes, required for orjson
        self._redis = aredis.from_url(self._url, decode_responses=False)
        await self._redis.ping()

    async def close(self) -> None:
        """Close the Redis connection pool."""
        if self._redis:
            await self._redis.aclose()  # type: ignore
            self._redis = None

    def _get_redis(self) -> aredis.Redis:
        """Helper to ensure Redis connection is initialized before use."""
        if self._redis is None:
            raise RuntimeError("Redis connection not initialized.")
        return self._redis

    def _make_key(self, key: str) -> str:
        """Prepend the configured prefix to the cache key."""
        return f"{self._prefix}{key}"

    async def ping(self) -> bool:
        """Check if the Redis connection is alive."""
        # Ping initialization check is inside get_redis, usually we want that to fail explicitly
        # or return False. Let's keep it explicitly failing if not init, but False if connection lost.
        try:
            redis = self._get_redis()  # Raises RuntimeError if not init
            return await redis.ping()
        except Exception as e:
            self._logger.error(f"Redis ping error: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from Redis, deserializing it with orjson."""
        redis = self._get_redis()
        full_key = self._make_key(key)
        try:
            data = await redis.get(full_key)
            if data is None:
                return None

            return orjson.loads(data)
        except Exception as e:
            self._logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value in Redis, serializing it with orjson."""
        redis = self._get_redis()
        full_key = self._make_key(key)
        try:
            expiration = ttl if ttl is not None else self._default_ttl

            dumped = orjson.dumps(value)
            await redis.set(full_key, dumped, ex=expiration)
        except Exception as e:
            self._logger.error(f"Cache set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete a specific key from Redis."""
        redis = self._get_redis()
        full_key = self._make_key(key)
        try:
            await redis.delete(full_key)
        except Exception as e:
            self._logger.error(f"Cache delete error: {e}")

    async def clear(self, prefix: Optional[str] = None) -> None:
        """Clear keys matching a pattern from Redis."""
        redis = self._get_redis()
        try:
            match_pattern = f"{self._prefix}{prefix or ''}*"

            # Iterate using scan to avoid blocking Redis
            keys: List[Any] = [k async for k in redis.scan_iter(match=match_pattern)]
            if keys:
                await redis.delete(*keys)
        except Exception as e:
            self._logger.error(f"Cache clear error: {e}")

    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in Redis."""
        redis = self._get_redis()
        full_key = self._make_key(key)
        try:
            return int(await redis.incrby(full_key, amount))
        except Exception as e:
            self._logger.error(f"Cache incr error: {e}")
            return None

    async def expire(self, key: str, ttl: int) -> None:
        """Set expiration time for a key."""
        redis = self._get_redis()
        full_key = self._make_key(key)
        try:
            await redis.expire(full_key, ttl)
        except Exception as e:
            self._logger.error(f"Cache expire error: {e}")

    async def _load_incr_script(self) -> None:
        """Loads and caches the SHA1 hash of the INCR/EXPIRE Lua script."""
        script = """
        local count = redis.call('INCR', KEYS[1])
        if count == 1 then
          redis.call('EXPIRE', KEYS[1], ARGV[1])
        end
        return count
        """
        redis = self._get_redis()
        self._incr_script_sha = await redis.script_load(script)

    async def incr_with_expire(
        self, key: str, amount: int = 1, ttl: Optional[int] = None
    ) -> Optional[int]:
        """
        Atomically increments a key and sets its TTL if it's a new key.
        Returns None on failure (fail-silent).
        """
        # PYLANCE FIX: Calculate full_key BEFORE the try block.
        # If _get_redis() fails inside try, full_key is already safe for logging.
        redis = self._get_redis()
        full_key = self._make_key(key)

        try:
            expire = ttl if ttl is not None else self._default_ttl

            # Ensure script is loaded
            if self._incr_script_sha is None:
                await self._load_incr_script()

            try:
                count = await redis.evalsha(
                    self._incr_script_sha,  # type: ignore
                    1,  # numkeys
                    full_key,  # keys
                    str(expire),  # args
                )
                self._logger.debug(
                    f"Atomic incr/expire for key: {full_key} (ttl={expire})"
                )
                return int(count)

            except NoScriptError:
                self._logger.warning(
                    "Lua script not found on Redis server, reloading..."
                )
                await self._load_incr_script()
                # Retry once
                return await self.incr_with_expire(key, amount, ttl)

        except Exception as e:
            # Now full_key is guaranteed to be bound
            self._logger.error(f"Atomic incr/expire error for key {full_key}: {e}")
            return None
