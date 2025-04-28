from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

import fastcore.db.engine as db_engine
from fastcore.config.base import BaseAppSettings
from fastcore.db.engine import init_db, shutdown_db
from fastcore.errors.exceptions import DBError
from fastcore.logging import Logger, ensure_logger


def setup_db(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[Logger] = None,
) -> None:
    """
    Configure database lifecycle for FastAPI application.

    - On startup: initialize AsyncEngine and sessionmaker
    - On shutdown: dispose engine
    """
    log = ensure_logger(logger, __name__, settings)

    async def on_startup():
        await init_db(settings, log)
        log.info("Database engine initialized")

    async def on_shutdown():
        await shutdown_db(log)
        log.info("Database engine disposed")

    app.add_event_handler("startup", on_startup)
    app.add_event_handler("shutdown", on_shutdown)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    """
    log = ensure_logger(None, __name__)

    log.warning(
        f"get_db: SessionLocal={db_engine.SessionLocal!r}, id={id(db_engine.SessionLocal)}, module={getattr(db_engine.SessionLocal, '__module__', None)}"
    )

    if db_engine.SessionLocal is None:
        raise DBError(message="Database not initialized")

    async with db_engine.SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            log.error(f"Database session error: {e}")
            raise DBError(message=str(e), details={"error": str(e)})
