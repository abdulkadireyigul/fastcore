"""
Database integration module for FastCore: public API
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
