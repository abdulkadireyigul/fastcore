import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from fastcore.db.base import BaseModel


class TokenType(str, enum.Enum):
    """Enum for token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class Token(BaseModel):
    """
    Represents a JWT token record for stateful token tracking.
    This model stores token metadata to enable validation and revocation,
    making the token system stateful despite using JWTs.
    """

    __tablename__ = "tokens"
    token_id = Column(String, unique=True, nullable=False, index=True)
    token_type = Column(Enum(TokenType), nullable=False, default=TokenType.ACCESS)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
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
