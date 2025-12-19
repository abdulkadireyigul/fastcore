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

import sys
import traceback
import warnings
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from fastcore.db.base import BaseModel
from fastcore.logging import ensure_logger
from fastcore.security.tokens.types import TokenType

logger = ensure_logger(None, __name__)

# --- IMPORT TRACER (Legacy Model) ---
# Inspect the stack to find who imported this file, ignoring importlib noise.
_stack = traceback.extract_stack()
_caller = next(
    (
        f
        for f in reversed(_stack)
        if "importlib" not in f.filename and f.filename != __file__
    ),
    None,
)

if _caller:
    logger.info(  # type: ignore
        f"\n[IMPORT TRACER] 'Legacy Token Model' (Integer) loaded."
        f"\n1. Triggered by: {_caller.filename}"
        f"\n2. Line Number : {_caller.lineno}"
    )

# --- CONFLICT GUARD ---
if "fastcore.security.tokens.uuid.models" in sys.modules:
    full_stack = traceback.extract_stack()

    filtered_stack = [
        frame
        for frame in full_stack
        if "<frozen" not in frame.filename and "importlib" not in frame.filename
    ]

    clean_traceback = "".join(traceback.format_list(filtered_stack))

    log_message = (
        "\nCRITICAL MODEL CONFLICT DETECTED!\n"
        "---------------------------------------\n"
        "The 'Legacy Token (Integer)' model is being imported, but 'UUID Token' is already loaded.\n"
        "This will cause database schema conflicts (both map to 'tokens' table).\n"
        "\n"
        "IMPORT TRACEBACK (Who triggered this import?):\n"
        f"{clean_traceback}\n"
        "---------------------------------------"
    )

    logger.warning(log_message)  # type: ignore

    warnings.warn(
        "Both Token models imported! See logs for full traceback.",
        RuntimeWarning,
        stacklevel=2,
    )


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
