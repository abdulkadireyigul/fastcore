"""
Database integration module for FastCore: public API

Features:
- Async SQLAlchemy integration (PostgreSQL+asyncpg or SQLite+aiosqlite)
- Repository pattern for CRUD and custom queries
- FastAPI dependency for session access
- Lifecycle management for FastAPI apps

Limitations:
- Only async SQLAlchemy is supported (no sync engine/session)
- No migration helpers (Alembic integration not included)
- No automatic model discovery/registration
- No advanced pool management or multi-DB support
"""
from fastcore.db.base import Base, metadata
from fastcore.db.engine import SessionLocal, engine, init_db, shutdown_db
from fastcore.db.manager import get_db, setup_db
from fastcore.db.repository import BaseRepository

__all__ = [
    "init_db",
    "shutdown_db",
    "engine",
    "SessionLocal",
    "setup_db",
    "get_db",
    "BaseRepository",
    "Base",
    "metadata",
]
