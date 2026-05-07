"""
UUID Database Configuration Module.

This module defines the base model and custom types for UUID-based database entities.
It isolates the UUID logic from the legacy Integer-based models found in `fastcore.db.base`.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator
from uuid6 import uuid7

# We import the existing Base from the core module to share the same MetaData.
# This ensures that Alembic can detect both legacy and new UUID tables in the same migration.
from fastcore.db.base import Base


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's native UUID type when available for efficiency.
    Otherwise, uses CHAR(36) to store UUIDs as stringified hex values (e.g., for SQLite).
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(pgUUID())
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class UUIDBaseModel(Base):
    """
    Base model for all UUID-based SQLAlchemy models.

    Features:
    - Uses UUID v7 as the primary key (sortable, unique).
    - Includes automatic timestamp columns (created_at, updated_at).
    - Inherits from the shared 'Base' to register with the application's metadata.
    """

    __abstract__ = True

    # Primary Key: UUID v7
    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid7, index=True
    )

    # Common Timestamp Columns
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )
