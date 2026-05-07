"""
Manual benchmark to measure REAL execution time of async cache operations.
"""

import time
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
from pydantic import BaseModel

from fastcore.cache.decorators import cache

# --- Setup Models & Data ---


class Item(BaseModel):
    id: int
    name: str
    attributes: Dict[str, int]


class ComplexResponse(BaseModel):
    items: List[Item]
    meta: Dict[str, str]


# 1000 elemanlı ağır veri
DATA_SIZE = 1000
heavy_data = ComplexResponse(
    items=[
        Item(id=i, name=f"item_{i}", attributes={"a": i, "b": i * 2})
        for i in range(DATA_SIZE)
    ],
    meta={"total": str(DATA_SIZE), "source": "benchmark"},
)

# Mock Redis Data (Bytes)
cached_bytes = orjson.dumps(heavy_data.model_dump(mode="json"))


@pytest.fixture
def mock_cache_instance():
    mock = AsyncMock()
    mock.get.return_value = orjson.loads(cached_bytes)
    mock._logger = MagicMock()
    return mock


@pytest.mark.asyncio
async def test_measure_execution_time_difference(mock_cache_instance):
    """
    Runs the decorated function multiple times and measures total execution time.
    """
    ITERATIONS = 100  # Toplam döngü sayısı

    with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache_instance):
        # 1. STANDARD (Validation VAR)
        @cache(ttl=60, return_raw=False)
        async def get_standard() -> ComplexResponse:
            return heavy_data

        # 2. OPTIMIZED (Validation YOK - Raw)
        @cache(ttl=60, return_raw=True)
        async def get_optimized() -> ComplexResponse:
            return heavy_data

        # --- Warmup ---
        await get_standard()
        await get_optimized()

        # --- Measure Standard ---
        start_std = time.perf_counter()
        for _ in range(ITERATIONS):
            res = await get_standard()
            # Emin olmak için tip kontrolü (validasyon yapıldı mı?)
            assert isinstance(res, ComplexResponse)
        end_std = time.perf_counter()
        avg_std = (end_std - start_std) / ITERATIONS

        # --- Measure Optimized ---
        start_opt = time.perf_counter()
        for _ in range(ITERATIONS):
            res = await get_optimized()
            # Emin olmak için tip kontrolü (dict mi döndü?)
            assert isinstance(res, dict)
        end_opt = time.perf_counter()
        avg_opt = (end_opt - start_opt) / ITERATIONS

        # --- Report ---
        print("\n" + "=" * 50)
        print(f"📊 BENCHMARK RESULTS ({ITERATIONS} iterations)")
        print("=" * 50)
        print(f"🐢 Standard (Model Validate): {avg_std*1000:.4f} ms / call")
        print(f"🚀 Optimized (Return Raw)  : {avg_opt*1000:.4f} ms / call")

        speedup = avg_std / avg_opt
        print(f"⚡ Speedup Factor          : {speedup:.2f}x FASTER")
        print("=" * 50 + "\n")
