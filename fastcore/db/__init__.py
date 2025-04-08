"""
Database utilities for FastAPI applications.

This module provides common database utilities for FastAPI applications,
including connection management, session handling, and base CRUD operations.
"""

from fastcore.db.repository import (
    BaseRepository,
    CreateSchemaType,
    ModelType,
    UpdateSchemaType,
)
from fastcore.db.session import (
    Base,
    Session,
    SessionLocal,
    db_dependency,
    engine,
    get_db,
    initialize_db,
)

__all__ = [
    # Session management
    "get_db",
    "Session",
    "SessionLocal",
    "Base",
    "engine",
    "initialize_db",
    "db_dependency",
    # Repository pattern
    "BaseRepository",
    "ModelType",
    "CreateSchemaType",
    "UpdateSchemaType",
]
