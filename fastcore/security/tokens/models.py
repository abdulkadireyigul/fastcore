"""
Token models for stateful JWT authentication.

This module defines SQLAlchemy models for tokens and token types.

Limitations:
- Only password-based JWT authentication is included by default
- No OAuth2 authorization code, implicit, or client credentials flows
- No social login (Google, Facebook, etc.)
- No multi-factor authentication
- No user registration or management flows (only protocols/interfaces)
- No advanced RBAC or permission system
- No API key support
- Stateless JWT blacklisting/revocation requires stateful DB tracking
"""

import enum
import sys
import warnings
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from fastcore.db.base import BaseModel

# --- CONFLICT GUARD ---
# Eğer UUID modülü zaten hafızadaysa uyar.
if "fastcore.security.tokens.uuid.models" in sys.modules:
    warnings.warn(
        "\n\nCRITICAL CONFIGURATION WARNING!\n"
        "---------------------------------------\n"
        "Both 'UUID Token' and 'Legacy Token (Integer)' models are imported detected!\n"
        "Since both map to the 'tokens' table, the last imported model will OVERWRITE the database schema.\n"
        "Please ensure your application imports ONLY ONE of these modules.\n"
        "If you are running tests, you can ignore this warning.\n",
        RuntimeWarning,
        stacklevel=2,
    )


class TokenType(str, enum.Enum):
    """
    Enum for token types.

    Features:
    - Supports access and refresh tokens

    Limitations:
    - Only password-based JWT authentication is included by default
    - No advanced RBAC or permission system
    """

    ACCESS = "access"
    REFRESH = "refresh"


class Token(BaseModel):
    """
    Represents a JWT token record for stateful token tracking.

    Features:
    - Stores token metadata for validation and revocation
    - Enables stateful JWT authentication

    Limitations:
    - Only password-based JWT authentication is included by default
    - No advanced RBAC or permission system
    - Stateless JWT blacklisting/revocation requires stateful DB tracking
    """

    __tablename__ = "tokens"
    token_id = Column(String, unique=True, nullable=False, index=True)
    token_type = Column(Enum(TokenType), nullable=False, default=TokenType.ACCESS)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    user = relationship("User", back_populates="tokens")

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
