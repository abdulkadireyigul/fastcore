"""
Database integration module for FastCore: public API
"""
from src.db.base import Base, metadata
from src.db.engine import SessionLocal, engine, init_db, shutdown_db
from src.db.manager import get_db, setup_db
from src.db.repository import BaseRepository

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
