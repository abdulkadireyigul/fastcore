"""
Comprehensive Benchmark: Hit vs Miss Latency Analysis
"""

import gc
import time
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
from pydantic import BaseModel

from fastcore.cache.decorators import cache


# --- Data Setup ---
class Item(BaseModel):
    id: int
    name: str
    attributes: Dict[str, int]


class ComplexResponse(BaseModel):
    items: List[Item]
    meta: Dict[str, str]


# 1000 items - Heavy Load
DATA_SIZE = 10000
heavy_data = ComplexResponse(
    items=[
        Item(id=i, name=f"item_{i}", attributes={"a": i, "b": i * 2})
        for i in range(DATA_SIZE)
    ],
    meta={"total": str(DATA_SIZE), "source": "benchmark"},
)

# Pre-calculate bytes for mocking Redis
cached_bytes = orjson.dumps(heavy_data.model_dump(mode="json"))


def get_mock_cache(mode="hit"):
    """Returns a mock cache instance configured for HIT or MISS."""
    mock = AsyncMock()
    mock._logger = MagicMock()
    if mode == "hit":
        # HIT: Return data immediately
        mock.get.return_value = orjson.loads(cached_bytes)
    else:
        # MISS: Return None
        mock.get.return_value = None
    return mock


@pytest.mark.asyncio
async def test_benchmark_hit_miss_comparison():
    ITERATIONS = 100

    print("\n" + "=" * 80)
    print(f"📊 HIT vs MISS BENCHMARK ({ITERATIONS} iterations)")
    print("=" * 80)

    # ---------------------------------------------------------
    # SCENARIO 1: STANDARD MODE (return_raw=False)
    # ---------------------------------------------------------
    print(f"\n🔹 STANDARD MODE (Pydantic Validation ON)")

    # 1.1 Standard MISS
    mock_miss = get_mock_cache("miss")
    with patch("fastcore.cache.decorators.get_cache", return_value=mock_miss):

        @cache(ttl=60, return_raw=False)
        async def get_std_miss() -> ComplexResponse:
            return heavy_data  # Simulating DB return

        # Warmup
        await get_std_miss()

        gc.collect()
        start = time.perf_counter()
        for _ in range(ITERATIONS):
            await get_std_miss()
        end = time.perf_counter()
        avg_std_miss = (end - start) / ITERATIONS
        print(f"  • MISS (Exec + Serialize + Write): {avg_std_miss*1000:.4f} ms")

    # 1.2 Standard HIT
    mock_hit = get_mock_cache("hit")
    with patch("fastcore.cache.decorators.get_cache", return_value=mock_hit):

        @cache(ttl=60, return_raw=False)
        async def get_std_hit() -> ComplexResponse:
            return heavy_data

        # Warmup
        await get_std_hit()

        gc.collect()
        start = time.perf_counter()
        for _ in range(ITERATIONS):
            await get_std_hit()
        end = time.perf_counter()
        avg_std_hit = (end - start) / ITERATIONS
        print(f"  • HIT  (Read + Validate)         : {avg_std_hit*1000:.4f} ms")

    # ---------------------------------------------------------
    # SCENARIO 2: OPTIMIZED MODE (return_raw=True)
    # ---------------------------------------------------------
    print(f"\n🔹 OPTIMIZED MODE (return_raw=True)")

    # 2.1 Optimized MISS
    mock_miss_opt = get_mock_cache("miss")
    with patch("fastcore.cache.decorators.get_cache", return_value=mock_miss_opt):

        @cache(ttl=60, return_raw=True)
        async def get_opt_miss() -> ComplexResponse:
            return heavy_data

        # Warmup
        await get_opt_miss()

        gc.collect()
        start = time.perf_counter()
        for _ in range(ITERATIONS):
            await get_opt_miss()
        end = time.perf_counter()
        avg_opt_miss = (end - start) / ITERATIONS
        print(f"  • MISS (Exec + Serialize + Write): {avg_opt_miss*1000:.4f} ms")

    # 2.2 Optimized HIT
    mock_hit_opt = get_mock_cache("hit")
    with patch("fastcore.cache.decorators.get_cache", return_value=mock_hit_opt):

        @cache(ttl=60, return_raw=True)
        async def get_opt_hit() -> ComplexResponse:
            return heavy_data

        # Warmup
        await get_opt_hit()

        gc.collect()
        start = time.perf_counter()
        for _ in range(ITERATIONS):
            await get_opt_hit()
        end = time.perf_counter()
        avg_opt_hit = (end - start) / ITERATIONS
        print(f"  • HIT  (Read + Raw Dict)         : {avg_opt_hit*1000:.4f} ms")

    print("-" * 80)
