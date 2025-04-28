"""
Database models for the security module.

This module defines the SQLAlchemy models used for security-related data,
particularly for stateful token management.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID

from fastcore.db.base import Base


class TokenType(str, enum.Enum):
    """Enum for token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class Token(Base):
    """
    Represents a JWT token record for stateful token tracking.

    This model stores token metadata to enable validation and revocation,
    making the token system stateful despite using JWTs.

    Notes:
        - user_id is stored as a string to avoid direct dependency on the User model
        - This allows the application to define its own User model structure
    """

    __tablename__ = "tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    token_type = Column(Enum(TokenType), nullable=False, default=TokenType.ACCESS)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<Token(token_id={self.token_id}, user_id={self.user_id}, type={self.token_type}, revoked={self.revoked})>"

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return self.expires_at < datetime.now(timezone.utc)

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not revoked and not expired)."""
        return not self.revoked and not self.is_expired
