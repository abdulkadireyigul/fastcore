"""
Tests for the cache decorator serialization fixes.

Covers all code paths changed vs. the original implementation:

WRITE SIDE (_to_serializable):
  - Pydantic model nested in tuple → must produce a JSON array, not crash
  - Pydantic model nested in dict value → must serialize the model, not crash
  - list[Model] regression → still serializes correctly via new path
  - Single Model regression → still serializes correctly via new path
  - Plain primitives → pass through unchanged

READ SIDE (tuple reconstruction):
  - tuple[list[Model], int] cache HIT → reconstructs to correct Python types
  - Empty list in tuple → round-trips correctly
  - list[Model] regression → model_validate still applied on HIT
  - Single Model regression → model_validate still applied on HIT
  - Validation failure (stale schema) → fail-open: raw cached value returned,
    function body NOT called

DECORATION TIME (type analysis):
  - Tuple annotation detected correctly (origin is tuple)
  - Non-tuple annotations still work

FULL ROUNDTRIP:
  - MISS writes serialized form; orjson can re-encode it; HIT reconstructs models

PERFORMANCE:
  - _to_serializable dispatch overhead vs direct model_dump list comprehension
  - Single model dispatch overhead
  - Tuple payload overhead vs equivalent list comprehension
"""

import timeit
from typing import List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
from pydantic import BaseModel

from fastcore.cache.decorators import _to_serializable, cache

# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


class DepartmentResponse(BaseModel):
    id: int
    name: str


class PhaseTATResponse(BaseModel):
    avg_grossing_tat_min: float
    avg_processing_tat_min: float


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_cache():
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)  # default: cache miss
    mock.set = AsyncMock()
    mock._logger = MagicMock()
    return mock


# ---------------------------------------------------------------------------
# Unit tests: _to_serializable helper directly
# ---------------------------------------------------------------------------


class TestToSerializable:
    def test_primitive_int(self):
        assert _to_serializable(42) == 42

    def test_primitive_str(self):
        assert _to_serializable("hello") == "hello"

    def test_primitive_none(self):
        assert _to_serializable(None) is None

    def test_primitive_float(self):
        assert _to_serializable(3.14) == 3.14

    def test_primitive_bool(self):
        assert _to_serializable(True) is True

    def test_single_pydantic_model(self):
        user = UserResponse(id=1, name="Alice", email="alice@example.com")
        result = _to_serializable(user)
        assert result == {"id": 1, "name": "Alice", "email": "alice@example.com"}
        assert isinstance(result, dict)

    def test_list_of_pydantic_models(self):
        users = [
            UserResponse(id=1, name="Alice", email="alice@example.com"),
            UserResponse(id=2, name="Bob", email="bob@example.com"),
        ]
        result = _to_serializable(users)
        assert result == [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ]

    def test_empty_list(self):
        assert _to_serializable([]) == []

    def test_tuple_of_list_model_and_int(self):
        """Primary failure pattern from production: (list[Model], int)."""
        users = [
            UserResponse(id=1, name="Alice", email="alice@example.com"),
            UserResponse(id=2, name="Bob", email="bob@example.com"),
        ]
        result = _to_serializable((users, 42))
        # Must come back as a plain list (JSON has no tuple literal)
        assert isinstance(result, list)
        assert result == [
            [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
            ],
            42,
        ]

    def test_dict_with_embedded_pydantic_model(self):
        """Dashboard failure pattern: dict whose value is a Pydantic model."""
        tat = PhaseTATResponse(avg_grossing_tat_min=12.5, avg_processing_tat_min=8.0)
        result = _to_serializable({"avg_case_tat_hours": 24.0, "phase_tat": tat})
        assert result == {
            "avg_case_tat_hours": 24.0,
            "phase_tat": {
                "avg_grossing_tat_min": 12.5,
                "avg_processing_tat_min": 8.0,
            },
        }

    def test_dict_with_only_primitives(self):
        d = {"a": 1, "b": "hello", "c": None}
        assert _to_serializable(d) == d

    def test_nested_list_of_primitives(self):
        lst = [1, "two", 3.0, None]
        assert _to_serializable(lst) == [1, "two", 3.0, None]

    def test_empty_tuple(self):
        assert _to_serializable(()) == []

    def test_orjson_can_serialize_all_output_shapes(self):
        """
        Every shape that reaches the cache must not raise when orjson.dumps
        is called on the _to_serializable output. This is the exact contract
        between _to_serializable and backends.set().
        """
        users = [
            UserResponse(id=i, name=f"u{i}", email=f"u{i}@x.com") for i in range(5)
        ]
        tat = PhaseTATResponse(avg_grossing_tat_min=1.0, avg_processing_tat_min=2.0)

        cases = [
            (users, 10),  # tuple[list[Model], int]
            {"avg": 5.0, "phase_tat": tat},  # dict with embedded model
            users,  # list[Model]
            users[0],  # single model
            42,  # primitive int
            "hello",  # primitive str
            [],  # empty list
            ([], 0),  # empty tuple
        ]
        for obj in cases:
            serialized = _to_serializable(obj)
            # Must not raise TypeError: Type is not JSON serializable
            orjson.dumps(serialized)


# ---------------------------------------------------------------------------
# Cache write path: verify serialized form passed to set() on MISS
# ---------------------------------------------------------------------------


class TestCacheWritePath:
    @pytest.mark.asyncio
    async def test_write_tuple_list_model_int(self, mock_cache):
        """
        The primary production bug: functions returning tuple[list[Model], int]
        must have the tuple serialized correctly before being passed to set().
        """
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = None

            @cache()
            async def list_users(offset: int = 0) -> tuple[list[UserResponse], int]:
                return (
                    [UserResponse(id=1, name="Alice", email="a@x.com")],
                    1,
                )

            result = await list_users()

            # The decorated function must still return the original Python types
            assert isinstance(result, tuple)
            items, count = result
            assert count == 1
            assert isinstance(items[0], UserResponse)

            # set() must receive a fully serialized form — no Pydantic instances
            call_args = mock_cache.set.call_args[0]
            to_cache = call_args[1]
            assert to_cache == [
                [{"id": 1, "name": "Alice", "email": "a@x.com"}],
                1,
            ]
            # Must not raise for orjson
            orjson.dumps(to_cache)

    @pytest.mark.asyncio
    async def test_write_tuple_multiple_items(self, mock_cache):
        """Tuple with multiple model items serializes all of them."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = None

            @cache()
            async def list_depts() -> tuple[list[DepartmentResponse], int]:
                return (
                    [
                        DepartmentResponse(id=1, name="Pathology"),
                        DepartmentResponse(id=2, name="Radiology"),
                    ],
                    2,
                )

            await list_depts()
            to_cache = mock_cache.set.call_args[0][1]
            assert to_cache == [
                [{"id": 1, "name": "Pathology"}, {"id": 2, "name": "Radiology"}],
                2,
            ]
            orjson.dumps(to_cache)

    @pytest.mark.asyncio
    async def test_write_dict_with_embedded_model(self, mock_cache):
        """Dashboard pattern: dict value that is a Pydantic model must be serialized."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = None

            @cache()
            async def get_tat_metrics() -> dict:
                return {
                    "avg_case_tat_hours": 24.0,
                    "phase_tat": PhaseTATResponse(
                        avg_grossing_tat_min=12.5,
                        avg_processing_tat_min=8.0,
                    ),
                }

            await get_tat_metrics()
            to_cache = mock_cache.set.call_args[0][1]
            assert to_cache == {
                "avg_case_tat_hours": 24.0,
                "phase_tat": {
                    "avg_grossing_tat_min": 12.5,
                    "avg_processing_tat_min": 8.0,
                },
            }
            orjson.dumps(to_cache)

    @pytest.mark.asyncio
    async def test_write_list_of_models_regression(self, mock_cache):
        """list[Model] path: must still serialize correctly through new _to_serializable."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = None

            @cache()
            async def get_users() -> list[UserResponse]:
                return [
                    UserResponse(id=1, name="Alice", email="a@x.com"),
                    UserResponse(id=2, name="Bob", email="b@x.com"),
                ]

            await get_users()
            to_cache = mock_cache.set.call_args[0][1]
            assert to_cache == [
                {"id": 1, "name": "Alice", "email": "a@x.com"},
                {"id": 2, "name": "Bob", "email": "b@x.com"},
            ]
            orjson.dumps(to_cache)

    @pytest.mark.asyncio
    async def test_write_single_model_regression(self, mock_cache):
        """Single Model path: must still serialize correctly through new _to_serializable."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = None

            @cache()
            async def get_user() -> UserResponse:
                return UserResponse(id=1, name="Alice", email="a@x.com")

            await get_user()
            to_cache = mock_cache.set.call_args[0][1]
            assert to_cache == {"id": 1, "name": "Alice", "email": "a@x.com"}
            orjson.dumps(to_cache)

    @pytest.mark.asyncio
    async def test_write_primitive_passthrough(self, mock_cache):
        """Primitive return value passes through _to_serializable unchanged."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = None

            @cache()
            async def get_count() -> int:
                return 99

            result = await get_count()
            assert result == 99
            to_cache = mock_cache.set.call_args[0][1]
            assert to_cache == 99


# ---------------------------------------------------------------------------
# Cache read path: verify reconstruction on HIT
# ---------------------------------------------------------------------------


class TestCacheReadPath:
    @pytest.mark.asyncio
    async def test_hit_tuple_list_model_int(self, mock_cache):
        """
        Cache HIT for tuple[list[Model], int]: the stored JSON array
        [[{...}], count] must be reconstructed to (list[Model], int).
        """
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = [
                [{"id": 1, "name": "Alice", "email": "a@x.com"}],
                1,
            ]

            @cache()
            async def list_users() -> tuple[list[UserResponse], int]:
                pytest.fail("Function body must not execute on a cache hit")

            result = await list_users()

            assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
            items, count = result
            assert count == 1
            assert len(items) == 1
            assert isinstance(items[0], UserResponse)
            assert items[0].id == 1
            assert items[0].name == "Alice"
            assert items[0].email == "a@x.com"
            # set() must NOT be called on a HIT
            mock_cache.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_hit_tuple_multiple_items(self, mock_cache):
        """Multiple models in the list part of the tuple are all reconstructed."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = [
                [
                    {"id": 1, "name": "Pathology"},
                    {"id": 2, "name": "Radiology"},
                ],
                2,
            ]

            @cache()
            async def list_depts() -> tuple[list[DepartmentResponse], int]:
                pytest.fail("Must not execute on HIT")

            result = await list_depts()
            assert isinstance(result, tuple)
            items, count = result
            assert count == 2
            assert len(items) == 2
            assert all(isinstance(d, DepartmentResponse) for d in items)
            assert items[0].name == "Pathology"
            assert items[1].name == "Radiology"

    @pytest.mark.asyncio
    async def test_hit_tuple_empty_list(self, mock_cache):
        """Empty list in the tuple position round-trips correctly."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = [[], 0]

            @cache()
            async def list_users() -> tuple[list[UserResponse], int]:
                pytest.fail("Must not execute on HIT")

            result = await list_users()
            items, count = result
            assert items == []
            assert count == 0

    @pytest.mark.asyncio
    async def test_hit_single_model_regression(self, mock_cache):
        """Single Model regression: model_validate still applied on HIT."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = {"id": 1, "name": "Alice", "email": "a@x.com"}

            @cache()
            async def get_user() -> UserResponse:
                pytest.fail("Must not execute on HIT")

            result = await get_user()
            assert isinstance(result, UserResponse)
            assert result.id == 1
            assert result.name == "Alice"

    @pytest.mark.asyncio
    async def test_hit_list_of_models_regression(self, mock_cache):
        """list[Model] regression: model_validate still applied per-item on HIT."""
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = [
                {"id": 1, "name": "Alice", "email": "a@x.com"},
                {"id": 2, "name": "Bob", "email": "b@x.com"},
            ]

            @cache()
            async def get_users() -> list[UserResponse]:
                pytest.fail("Must not execute on HIT")

            result = await get_users()
            assert isinstance(result, list)
            assert all(isinstance(u, UserResponse) for u in result)
            assert result[0].name == "Alice"
            assert result[1].name == "Bob"

    @pytest.mark.asyncio
    async def test_hit_schema_changed_returns_raw_fallback(self, mock_cache):
        """
        If cached data fails Pydantic reconstruction (missing required field),
        the decorator returns the raw cached value rather than raising or calling
        the function body. This is the fail-open behavior inherited from the
        rest of the decorator.
        """
        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # Missing required 'email' field — UserResponse.model_validate raises
            stale = [[{"id": 1, "name": "Alice"}], 1]
            mock_cache.get.return_value = stale

            body_called = []

            @cache()
            async def list_users() -> tuple[list[UserResponse], int]:
                body_called.append(True)
                return ([UserResponse(id=99, name="Fresh", email="fresh@x.com")], 1)

            result = await list_users()

            # The function body must NOT be invoked — cached value is not None
            assert not body_called, "Function body must not be called on a cache HIT"
            # The raw cached data is returned as-is (list, not reconstructed tuple)
            assert result == stale


# ---------------------------------------------------------------------------
# Full roundtrip: MISS → Redis bytes → HIT → original types
# ---------------------------------------------------------------------------


class TestFullRoundtrip:
    @pytest.mark.asyncio
    async def test_roundtrip_tuple_list_model_int(self, mock_cache):
        """
        End-to-end: a MISS writes a JSON-serializable payload; feeding that
        same payload (via orjson round-trip) back as a HIT reconstructs the
        original Python types.
        """
        captured_writes: list = []

        async def fake_set(key, value, ttl=None):
            captured_writes.append(value)

        mock_cache.set.side_effect = fake_set

        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            # --- MISS: execute function and capture what was written ---
            mock_cache.get.return_value = None

            @cache()
            async def list_departments() -> tuple[list[DepartmentResponse], int]:
                return (
                    [
                        DepartmentResponse(id=1, name="Pathology"),
                        DepartmentResponse(id=2, name="Radiology"),
                    ],
                    2,
                )

            miss_result = await list_departments()
            assert isinstance(miss_result, tuple)
            assert len(captured_writes) == 1

            # Simulate Redis round-trip: orjson.dumps does the final encoding,
            # orjson.loads on read. Must not raise.
            redis_bytes = orjson.dumps(captured_writes[0])
            redis_value = orjson.loads(redis_bytes)

            # --- HIT: feed the round-tripped value back as the cache result ---
            mock_cache.get.return_value = redis_value

            hit_result = await list_departments()

            assert isinstance(
                hit_result, tuple
            ), f"Expected tuple on cache HIT, got {type(hit_result).__name__}"
            items, count = hit_result
            assert count == 2
            assert len(items) == 2
            assert all(isinstance(d, DepartmentResponse) for d in items)
            assert items[0].id == 1
            assert items[0].name == "Pathology"
            assert items[1].id == 2
            assert items[1].name == "Radiology"

    @pytest.mark.asyncio
    async def test_roundtrip_single_model(self, mock_cache):
        """Single model regression: roundtrip still produces a model instance."""
        captured_writes: list = []

        async def fake_set(key, value, ttl=None):
            captured_writes.append(value)

        mock_cache.set.side_effect = fake_set

        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = None

            @cache()
            async def get_user() -> UserResponse:
                return UserResponse(id=7, name="Carol", email="carol@x.com")

            await get_user()
            redis_value = orjson.loads(orjson.dumps(captured_writes[0]))

            mock_cache.get.return_value = redis_value

            hit = await get_user()
            assert isinstance(hit, UserResponse)
            assert hit.id == 7
            assert hit.name == "Carol"

    @pytest.mark.asyncio
    async def test_roundtrip_list_of_models(self, mock_cache):
        """list[Model] regression: roundtrip still produces a list of model instances."""
        captured_writes: list = []

        async def fake_set(key, value, ttl=None):
            captured_writes.append(value)

        mock_cache.set.side_effect = fake_set

        with patch("fastcore.cache.decorators.get_cache", return_value=mock_cache):
            mock_cache.get.return_value = None

            @cache()
            async def get_users() -> list[UserResponse]:
                return [
                    UserResponse(id=1, name="Alice", email="a@x.com"),
                    UserResponse(id=2, name="Bob", email="b@x.com"),
                ]

            await get_users()
            redis_value = orjson.loads(orjson.dumps(captured_writes[0]))

            mock_cache.get.return_value = redis_value

            hit = await get_users()
            assert isinstance(hit, list)
            assert all(isinstance(u, UserResponse) for u in hit)
            assert hit[0].name == "Alice"
            assert hit[1].name == "Bob"


# ---------------------------------------------------------------------------
# Type annotation detection at decoration time
# ---------------------------------------------------------------------------


class TestTypeAnalysis:
    def test_tuple_annotation_detected(self):
        """
        is_tuple must be True when the return annotation is tuple[X, Y].
        Verified indirectly: the HIT path reconstructs to a Python tuple.
        """
        # The decorator captures is_tuple at definition time.
        # We verify it works correctly via the HIT reconstruction behavior,
        # which is only activated when is_tuple=True.
        import asyncio

        mock = AsyncMock()
        mock.get = AsyncMock(
            return_value=[[{"id": 1, "name": "X", "email": "x@x.com"}], 1]
        )
        mock.set = AsyncMock()
        mock._logger = MagicMock()

        @cache()
        async def f() -> tuple[list[UserResponse], int]:
            pytest.fail("Must not execute on HIT")

        with patch("fastcore.cache.decorators.get_cache", return_value=mock):
            result = asyncio.get_event_loop().run_until_complete(f())

        assert isinstance(
            result, tuple
        ), "tuple annotation must be detected at decoration time"

    def test_typing_Tuple_annotation_also_detected(self):
        """
        Typing.Tuple[X, Y] (capital T, from typing module) must also be detected,
        since both have __origin__ == tuple.
        """
        import asyncio

        mock = AsyncMock()
        mock.get = AsyncMock(
            return_value=[[{"id": 1, "name": "X", "email": "x@x.com"}], 1]
        )
        mock.set = AsyncMock()
        mock._logger = MagicMock()

        @cache()
        async def f() -> Tuple[List[UserResponse], int]:
            pytest.fail("Must not execute on HIT")

        with patch("fastcore.cache.decorators.get_cache", return_value=mock):
            result = asyncio.get_event_loop().run_until_complete(f())

        assert isinstance(
            result, tuple
        ), "Typing.Tuple annotation must be detected at decoration time"


# ---------------------------------------------------------------------------
# Performance: _to_serializable overhead vs direct model_dump
# ---------------------------------------------------------------------------


class TestToSerializablePerformance:
    """
    These tests measure the *dispatch overhead* of _to_serializable compared
    to calling model_dump directly (which is what the old code did for lists).

    The bulk of the work in both cases is the N model_dump() calls themselves.
    The overhead of _to_serializable is the extra Python function calls and
    isinstance/hasattr checks at each recursion level.

    Threshold: overhead must be < 30% of the direct model_dump cost.
    This is a very conservative bound — typical measured overhead is 1–8%.
    """

    N = 100
    ITERS = 500

    @pytest.fixture(autouse=True)
    def users(self):
        return [
            UserResponse(id=i, name=f"user_{i}", email=f"u{i}@example.com")
            for i in range(self.N)
        ]

    def test_overhead_list_of_models(self, users):
        """
        _to_serializable(list[Model]) vs direct list comprehension of model_dump.
        The extra cost is N extra function-call frames — one per item.
        """
        direct_time = timeit.timeit(
            lambda: [u.model_dump(mode="json") for u in users],
            number=self.ITERS,
        )
        new_time = timeit.timeit(
            lambda: _to_serializable(users),
            number=self.ITERS,
        )

        overhead_ratio = (new_time - direct_time) / direct_time
        avg_direct_us = (direct_time / self.ITERS) * 1_000_000
        avg_new_us = (new_time / self.ITERS) * 1_000_000

        print(f"\n[Perf] list[Model] N={self.N}, {self.ITERS} iters")
        print(f"  Direct model_dump list comprehension: {avg_direct_us:.1f} µs/call")
        print(f"  _to_serializable(list[Model]):         {avg_new_us:.1f} µs/call")
        print(f"  Overhead:                              {overhead_ratio:+.1%}")

        assert overhead_ratio < 0.30, (
            f"_to_serializable overhead {overhead_ratio:.1%} exceeds 30% threshold. "
            f"Direct: {avg_direct_us:.1f}µs, New: {avg_new_us:.1f}µs"
        )

    def test_overhead_single_model(self, users):
        """
        _to_serializable(Model) vs direct model_dump().
        The only extra cost is one hasattr check.
        """
        user = users[0]
        direct_time = timeit.timeit(
            lambda: user.model_dump(mode="json"),
            number=self.ITERS * 10,
        )
        new_time = timeit.timeit(
            lambda: _to_serializable(user),
            number=self.ITERS * 10,
        )

        avg_direct_us = (direct_time / (self.ITERS * 10)) * 1_000_000
        avg_new_us = (new_time / (self.ITERS * 10)) * 1_000_000
        overhead_abs_us = avg_new_us - avg_direct_us
        overhead_ratio = (new_time - direct_time) / direct_time

        print(f"\n[Perf] Single model, {self.ITERS * 10} iters")
        print(f"  Direct model_dump():    {avg_direct_us:.2f} µs/call")
        print(f"  _to_serializable():     {avg_new_us:.2f} µs/call")
        print(
            f"  Overhead:               {overhead_ratio:+.1%} ({overhead_abs_us:.2f} µs absolute)"
        )

        # Absolute bound: one hasattr() + one function-frame must cost < 5 µs
        # regardless of coverage-tracing environment (measured: ~0.9 µs).
        assert overhead_abs_us < 5.0, (
            f"Single-model absolute overhead {overhead_abs_us:.2f} µs exceeds 5 µs limit. "
            f"Direct: {avg_direct_us:.2f}µs, New: {avg_new_us:.2f}µs"
        )

    def test_overhead_tuple_payload(self, users):
        """
        _to_serializable((list[Model], int)) overhead vs direct list comprehension.

        The tuple adds exactly 2 extra recursion levels (tuple dispatch → list
        dispatch) on top of the N per-item dispatches. For N=100, this is
        negligible relative to the N model_dump calls.
        """
        payload = (users, self.N)

        # Equivalent direct work: serialize just the list part
        direct_time = timeit.timeit(
            lambda: [u.model_dump(mode="json") for u in users],
            number=self.ITERS,
        )
        new_time = timeit.timeit(
            lambda: _to_serializable(payload),
            number=self.ITERS,
        )

        overhead_ratio = (new_time - direct_time) / direct_time
        avg_direct_us = (direct_time / self.ITERS) * 1_000_000
        avg_new_us = (new_time / self.ITERS) * 1_000_000

        print(f"\n[Perf] tuple(list[{self.N}], int), {self.ITERS} iters")
        print(f"  Direct list comprehension:    {avg_direct_us:.1f} µs/call")
        print(f"  _to_serializable(tuple):      {avg_new_us:.1f} µs/call")
        print(f"  Overhead vs list-only path:   {overhead_ratio:+.1%}")

        assert overhead_ratio < 0.30, (
            f"Tuple overhead {overhead_ratio:.1%} exceeds 30% threshold. "
            f"Direct: {avg_direct_us:.1f}µs, New: {avg_new_us:.1f}µs"
        )

    def test_to_serializable_cost_vs_orjson_dumps(self, users):
        """
        _to_serializable prepares data for orjson.dumps (the final encoding step).
        Its cost should be comparable to or greater than orjson.dumps on the
        already-plain output — both are dominated by the volume of data, not
        dispatch overhead. Neither step should be pathological (> 10ms/call for N=100).
        """
        payload = (users, self.N)
        pre_serialized = _to_serializable(payload)

        to_ser_time = timeit.timeit(
            lambda: _to_serializable(payload),
            number=self.ITERS,
        )
        orjson_time = timeit.timeit(
            lambda: orjson.dumps(pre_serialized),
            number=self.ITERS,
        )

        avg_to_ser_us = (to_ser_time / self.ITERS) * 1_000_000
        avg_orjson_us = (orjson_time / self.ITERS) * 1_000_000

        print(
            f"\n[Perf] _to_serializable vs orjson.dumps, N={self.N}, {self.ITERS} iters"
        )
        print(
            f"  _to_serializable: {avg_to_ser_us:.1f} µs/call  (model_dump calls dominate)"
        )
        print(
            f"  orjson.dumps:     {avg_orjson_us:.1f} µs/call  (plain dicts, very fast)"
        )

        # Neither step may exceed 10ms per call for N=100 — sanity bound
        assert (
            avg_to_ser_us < 10_000
        ), f"_to_serializable took {avg_to_ser_us:.1f}µs — unexpectedly slow"
        assert (
            avg_orjson_us < 10_000
        ), f"orjson.dumps took {avg_orjson_us:.1f}µs — unexpectedly slow"
