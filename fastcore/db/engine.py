"""
Database engine and session management for FastAPI applications.
"""

from typing import Optional

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fastcore.config.base import BaseAppSettings
from fastcore.logging import Logger, ensure_logger

# Module-level engine and session factory
engine: Optional[AsyncEngine] = None
SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db(settings: BaseAppSettings, logger: Optional[Logger] = None) -> None:
    """
    Initialize the database engine and session factory.

    Args:
        settings: Application settings
        logger: Optional logger for database operations
    """
    global engine, SessionLocal

    # ensure_logger kullanarak tutarlı logging
    log = ensure_logger(logger, __name__, settings)

    log.debug(f"Creating database engine with URL: {settings.DATABASE_URL}")
    url = make_url(settings.DATABASE_URL)
    engine_kwargs = {
        "echo": settings.DB_ECHO,
    }
    # Only pass pool_size if not using SQLite+aiosqlite
    if not (
        url.get_backend_name() == "sqlite" and url.drivername.endswith("aiosqlite")
    ):
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine = create_async_engine(
        settings.DATABASE_URL,
        **engine_kwargs,
    )
    SessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    log.debug("Database engine and session factory initialized")


async def shutdown_db(logger: Optional[Logger] = None) -> None:
    """
    Dispose of the database engine.

    Args:
        logger: Optional logger for database operations
    """
    global engine

    # ensure_logger kullanarak tutarlı logging
    log = ensure_logger(logger, __name__)

    if engine:
        log.debug("Disposing database engine")
        await engine.dispose()
        log.debug("Database engine disposed")
