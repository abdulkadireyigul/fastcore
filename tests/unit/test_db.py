"""
Unit tests for the db module (engine, manager, repository).

Covers:
- All CRUD operations and error handling in BaseRepository
- Engine and session lifecycle (init_db, shutdown_db)
- FastAPI event handler registration and execution
- get_db dependency, including commit/rollback and error branches
- Logging and exception handling for all major code paths
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastcore.db.repository import BaseRepository
from fastcore.errors.exceptions import DBError, NotFoundError


@pytest.fixture
def dummy_session():
    return AsyncMock()


@pytest.fixture
def dummy_model():
    class DummyModel:
        __name__ = "DummyModel"

        def __init__(self, id=None, **kwargs):
            self.id = id
            for k, v in kwargs.items():
                setattr(self, k, v)

    return DummyModel


@pytest.mark.asyncio
async def test_repository_get_by_id_success(dummy_session, dummy_model):
    """Test get_by_id returns the correct model instance."""
    session = dummy_session
    session.get.return_value = dummy_model(id=1)
    repo = BaseRepository(dummy_model, session)
    result = await repo.get_by_id(1)
    assert isinstance(result, dummy_model)
    session.get.assert_awaited_once_with(dummy_model, 1)


@pytest.mark.asyncio
async def test_repository_get_by_id_not_found(dummy_session, dummy_model):
    """Test get_by_id raises NotFoundError if not found."""
    session = dummy_session
    session.get.return_value = None
    repo = BaseRepository(dummy_model, session)
    with pytest.raises(NotFoundError):
        await repo.get_by_id(2)


@pytest.mark.asyncio
async def test_repository_get_by_id_db_error(dummy_session, dummy_model):
    """Test get_by_id raises DBError on DB exception."""
    session = dummy_session
    session.get.side_effect = Exception("fail")
    repo = BaseRepository(dummy_model, session)
    with pytest.raises(DBError):
        await repo.get_by_id(3)


@pytest.mark.asyncio
async def test_repository_list_success(dummy_session, dummy_model):
    """Test list returns multiple model instances."""
    session = dummy_session
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [dummy_model(id=1), dummy_model(id=2)]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    repo = BaseRepository(dummy_model, session)
    with patch("src.db.repository.select", return_value=MagicMock()):
        items = await repo.list()
    assert len(items) == 2
    session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_repository_list_with_filters(dummy_session, dummy_model):
    """Test list returns filtered results."""
    session = dummy_session
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    repo = BaseRepository(dummy_model, session)
    with patch("src.db.repository.select", return_value=MagicMock()):
        items = await repo.list(filters={"id": 1})
    assert items == []
    session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_repository_list_db_error(dummy_session, dummy_model):
    """Test list raises DBError on DB exception."""
    session = dummy_session
    session.execute.side_effect = Exception("fail")
    repo = BaseRepository(dummy_model, session)
    with pytest.raises(DBError):
        await repo.list()


@pytest.mark.asyncio
async def test_repository_create_success(dummy_session, dummy_model):
    """Test create successfully adds a new model instance."""
    session = dummy_session
    session.flush.return_value = None
    repo = BaseRepository(dummy_model, session)
    data = {"id": 10, "foo": "bar"}
    obj = await repo.create(data)
    assert isinstance(obj, dummy_model)
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_create_db_error(dummy_session, dummy_model):
    """Test create raises DBError on DB exception."""
    session = dummy_session
    session.add.return_value = None
    session.flush.side_effect = Exception("fail")
    repo = BaseRepository(dummy_model, session)
    with patch.object(repo, "logger"):
        with pytest.raises(DBError):
            await repo.create({"id": 11})


@pytest.mark.asyncio
async def test_repository_update_success(dummy_session, dummy_model):
    """Test update successfully updates a model instance."""
    session = dummy_session
    dummy = dummy_model(id=1, foo="old")
    repo = BaseRepository(dummy_model, session)
    repo.get_by_id = AsyncMock(return_value=dummy)
    session.flush.return_value = None
    updated = await repo.update(1, {"foo": "new"})
    assert updated.foo == "new"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_update_db_error(dummy_session, dummy_model):
    """Test update raises DBError on DB exception."""
    session = dummy_session
    repo = BaseRepository(dummy_model, session)
    repo.get_by_id = AsyncMock(side_effect=Exception("fail"))
    with pytest.raises(DBError):
        await repo.update(1, {"foo": "bar"})


@pytest.mark.asyncio
async def test_repository_delete_success(dummy_session, dummy_model):
    """Test delete successfully removes a model instance."""
    session = dummy_session
    dummy = dummy_model(id=1)
    repo = BaseRepository(dummy_model, session)
    repo.get_by_id = AsyncMock(return_value=dummy)
    session.delete.return_value = None
    session.flush.return_value = None
    await repo.delete(1)
    session.delete.assert_awaited_once_with(dummy)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_delete_db_error(dummy_session, dummy_model):
    """Test delete raises DBError on DB exception."""
    session = dummy_session
    repo = BaseRepository(dummy_model, session)
    repo.get_by_id = AsyncMock(side_effect=Exception("fail"))
    with pytest.raises(DBError):
        await repo.delete(1)


def test_shutdown_db_no_engine(monkeypatch):
    """Test shutdown_db does nothing if engine is None."""
    db_engine_mod = sys.modules["src.db.engine"]
    monkeypatch.setattr(db_engine_mod, "engine", None)
    import asyncio

    asyncio.run(db_engine_mod.shutdown_db())


def test_shutdown_db_logs_when_engine(monkeypatch):
    """Test shutdown_db disposes engine and logs."""
    db_engine_mod = sys.modules["src.db.engine"]
    mock_engine = AsyncMock()
    monkeypatch.setattr(db_engine_mod, "engine", mock_engine)
    mock_engine.dispose.return_value = None
    import asyncio

    from fastcore.db.engine import shutdown_db

    asyncio.run(shutdown_db())
    mock_engine.dispose.assert_awaited_once()


def test_shutdown_db_logs_after_dispose(monkeypatch):
    """Test shutdown_db logs after engine is disposed."""
    db_engine_mod = sys.modules["src.db.engine"]
    mock_engine = AsyncMock()
    monkeypatch.setattr(db_engine_mod, "engine", mock_engine)
    mock_engine.dispose.return_value = None
    with patch("src.db.engine.ensure_logger") as mock_logger:
        import asyncio

        from fastcore.db.engine import shutdown_db

        asyncio.run(shutdown_db())
        assert any(
            "disposed" in str(call.args)
            for call in mock_logger.return_value.debug.call_args_list
        )


def test_setup_db_event_handlers_are_called(monkeypatch):
    """Test setup_db registers and calls event handlers."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastapi import FastAPI

    from fastcore.db.manager import setup_db

    app = FastAPI()
    settings = MagicMock()
    logger = MagicMock()
    setup_db(app, settings, logger)
    with patch("src.db.manager.init_db", new=AsyncMock()) as mock_init_db, patch(
        "src.db.manager.shutdown_db", new=AsyncMock()
    ) as mock_shutdown_db:
        import asyncio

        for handler in app.router.on_startup:
            asyncio.run(handler())
        for handler in app.router.on_shutdown:
            asyncio.run(handler())
        mock_init_db.assert_awaited()
        mock_shutdown_db.assert_awaited()


def test_init_db_logs_and_handles_exceptions(monkeypatch):
    """Test init_db logs and handles exceptions."""
    from fastcore.config.base import BaseAppSettings
    from fastcore.db.engine import init_db

    settings = MagicMock(spec=BaseAppSettings)
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    settings.DB_ECHO = False
    settings.DB_POOL_SIZE = 5
    logger = MagicMock()
    with patch("src.db.engine.create_async_engine", side_effect=Exception("fail")):
        with pytest.raises(Exception):
            import asyncio

            asyncio.run(init_db(settings, logger))


def test_shutdown_db_handles_exceptions(monkeypatch):
    """Test shutdown_db handles exceptions from engine.dispose."""
    db_engine_mod = sys.modules["src.db.engine"]
    mock_engine = AsyncMock()
    mock_engine.dispose.side_effect = Exception("fail")
    monkeypatch.setattr(db_engine_mod, "engine", mock_engine)
    from fastcore.db.engine import shutdown_db

    with pytest.raises(Exception):
        import asyncio

        asyncio.run(shutdown_db())


@pytest.mark.asyncio
async def test_get_db_commit_and_rollback(monkeypatch):
    """Test get_db commits on success and rolls back on error."""
    import fastcore.db.manager as db_manager_mod

    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = None
    monkeypatch.setattr(db_manager_mod, "SessionLocal", lambda: mock_cm)
    from fastcore.db.manager import get_db

    gen = get_db()
    session = await gen.__anext__()
    with pytest.raises(StopAsyncIteration):
        await gen.asend(None)
    mock_session.commit.assert_awaited_once()
    gen = get_db()
    session = await gen.__anext__()
    mock_session.commit.reset_mock()
    mock_session.rollback.reset_mock()
    with pytest.raises(DBError):
        await gen.athrow(Exception("fail"))
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_commit_exception(monkeypatch):
    """Test get_db rolls back and raises DBError if commit fails."""
    import fastcore.db.manager as db_manager_mod

    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = None
    monkeypatch.setattr(db_manager_mod, "SessionLocal", lambda: mock_cm)
    from fastcore.db.manager import get_db

    mock_session.commit.side_effect = Exception("commit fail")
    mock_session.rollback.return_value = None
    gen = get_db()
    session = await gen.__anext__()
    with pytest.raises(DBError):
        await gen.asend(None)
    mock_session.rollback.assert_awaited_once()
