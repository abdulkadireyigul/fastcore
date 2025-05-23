from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
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

    - On startup: initialize AsyncEngine and sessionmaker (async only)
    - On shutdown: dispose engine

    Limitations:
    - Only async SQLAlchemy is supported (no sync engine/session)
    - No migration helpers (Alembic integration not included)
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

    Only async SQLAlchemy is supported. No sync session support.
    """
    import sys

    log = ensure_logger(None, __name__)
    db_engine_mod = sys.modules.get("fastcore.db.engine")
    if db_engine_mod is None:
        import fastcore.db.engine as db_engine_mod
    SessionLocal = getattr(db_engine_mod, "SessionLocal", None)
    log.debug(
        f"get_db: SessionLocal={SessionLocal!r}, id={id(SessionLocal) if SessionLocal else None}, module={getattr(SessionLocal, '__module__', None) if SessionLocal else None}"
    )
    if SessionLocal is None:
        raise DBError(message="Database not initialized")
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except HTTPException as e:
            await session.rollback()
            log.error(f"Database session error (HTTPException): {e!r}")
            raise
        except Exception as e:
            await session.rollback()
            log.error(f"Database session error: {e!r}")
            raise DBError(message=str(e), details={"error": str(e)})
