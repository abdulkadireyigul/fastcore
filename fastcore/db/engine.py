"""
Database engine and session management for FastAPI applications.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fastcore.config.base import BaseAppSettings

# Module-level engine and session factory
engine: Optional[AsyncEngine] = None
SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db(settings: BaseAppSettings) -> None:
    """
    Initialize the database engine and session factory.
    """
    global engine, SessionLocal
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
    )
    SessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


async def shutdown_db() -> None:
    """
    Dispose of the database engine.
    """
    global engine
    if engine:
        await engine.dispose()
