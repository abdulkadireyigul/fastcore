"""
Base SQLAlchemy configuration for the application.

This module defines the base SQLAlchemy classes and metadata used throughout
the application. All models should inherit from the Base class defined here.
"""

from sqlalchemy import Column, DateTime, Integer, MetaData, func
from sqlalchemy.orm import declarative_base

# Define a consistent naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Create metadata with naming convention
metadata = MetaData(naming_convention=convention)

# Create declarative base class for all models
Base = declarative_base(metadata=metadata)


class BaseModel(Base):
    """Base model for all SQLAlchemy models."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )


__all__ = ["Base", "BaseModel", "metadata"]
