# Token package initialization

# Expose get_settings for testability
import jwt  # PyJWT

from fastcore.config.settings import get_settings

# Re-export all public API for patching/testing
from fastcore.security.tokens import models, repository, service, utils
from fastcore.security.tokens.repository import TokenRepository
from fastcore.security.tokens.service import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    refresh_access_token,
    revoke_token,
    validate_token,
)
from fastcore.security.tokens.utils import decode_token

# For patching in tests
__all__ = [
    "get_settings",
    "models",
    "repository",
    "service",
    "utils",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "refresh_access_token",
    "revoke_token",
    "validate_token",
    "decode_token",
    "jwt",
    "TokenRepository",
]
