"""
UUID Token Models Module.

This module defines the SQLAlchemy ORM model for storing JWT metadata using
UUIDs (Universally Unique Identifiers) as primary keys.

It serves as the persistence layer for the `UUIDTokenService`, allowing
stateful validation (e.g., checking revocation status) of JWTs in systems
where users are identified by UUIDs.
"""

import sys
import uuid
import warnings
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import our new UUID-based infrastructure
from fastcore.db.uuid.base import GUID, UUIDBaseModel

# Re-use the standard TokenType enum (shared constant)
from fastcore.security.tokens.models import TokenType

# --- CONFLICT GUARD ---
if "fastcore.security.tokens.models" in sys.modules:
    warnings.warn(
        "\n\nCRITICAL CONFIGURATION WARNING!\n"
        "---------------------------------------\n"
        "Both 'Legacy Token (Integer)' and 'UUID Token' models are imported detected!\n"
        "Since both map to the 'tokens' table, the last imported model will OVERWRITE the database schema.\n"
        "Please ensure your application imports ONLY ONE of these modules.\n"
        "If you are running tests, you can ignore this warning.\n",
        RuntimeWarning,
        stacklevel=2,
    )


class UUIDToken(UUIDBaseModel):
    """
    Represents a JWT token record with UUID primary keys.

    This model is used for stateful JWT authentication. It persists essential
    metadata about issued tokens to allow for revocation checks and
    active session management.

    Attributes:
        token_id (str): The unique JWT ID (jti) claim from the token payload.
        token_type (TokenType): The type of token (ACCESS or REFRESH).
        revoked (bool): Flag indicating if the token has been explicitly revoked.
        expires_at (datetime): The timestamp when the token expires.
        user_id (uuid.UUID): Foreign Key linking to the User model.
    """

    __tablename__ = "tokens"
    __table_args__ = {"extend_existing": True}

    # The JTI (JWT ID) claim from the token payload.
    # Used to uniquely identify a specific token instance.
    token_id: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )

    # Access or Refresh token discriminator.
    token_type: Mapped[TokenType] = mapped_column(
        Enum(TokenType), nullable=False, default=TokenType.ACCESS
    )

    # Revocation status.
    # If True, the token is considered invalid even if the signature is correct.
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Expiration timestamp.
    # Stored as a timezone-aware datetime object.
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Foreign Key to the Users table.
    # Utilizes the custom GUID type to ensure compatibility across DB drivers.
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Relationship to the User model.
    # 'Any' is used here to avoid circular imports if the User model is defined elsewhere.
    user: Mapped["Any"] = relationship("User", back_populates="tokens")

    @property
    def is_expired(self) -> bool:
        """
        Check if the token has expired based on the current UTC time.

        Returns:
            bool: True if the expiration time has passed, False otherwise.
        """
        return self.expires_at < datetime.now(timezone.utc)

    @property
    def is_valid(self) -> bool:
        """
        Check if the token is valid for use.

        A token is valid only if:
        1. It has NOT been explicitly revoked.
        2. It has NOT expired.

        Returns:
            bool: True if valid, False otherwise.
        """
        return not self.revoked and not self.is_expired

    def __repr__(self) -> str:
        """
        Return a string representation of the UUIDToken instance.
        """
        return (
            f"<UUIDToken(id={self.id}, token_id={self.token_id}, "
            f"user_id={self.user_id})>"
        )
