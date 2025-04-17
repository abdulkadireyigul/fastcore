"""
Database integration module for FastCore: public API
"""
from .engine import SessionLocal, engine, init_db, shutdown_db
from .manager import get_db, setup_db
from .repository import BaseRepository

__all__ = [
    "init_db",
    "shutdown_db",
    "engine",
    "SessionLocal",
    "setup_db",
    "get_db",
    "BaseRepository",
]
