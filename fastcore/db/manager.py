from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.config.base import BaseAppSettings
from fastcore.db.engine import SessionLocal, init_db, shutdown_db
from fastcore.errors.exceptions import DBError
from fastcore.logging import ensure_logger  # Python logging yerine kendi modülümüz


def setup_db(
    app: FastAPI,
    settings: BaseAppSettings,
    logger: Optional[object] = None,
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
    if SessionLocal is None:
        raise DBError(message="Database not initialized")

    log = ensure_logger(None, __name__)

    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            log.error(f"Database session error: {e}")
            raise DBError(message=str(e), details={"error": str(e)})
