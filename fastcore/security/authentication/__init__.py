"""
Authentication module for FastAPI applications.

This module provides functionality for user authentication, including
JWT token creation and validation.
"""

from .dependencies import (
    get_current_user_data,
    get_optional_user_data,
    get_user_with_claim,
)
from .jwt import create_access_token, create_token_response, decode_token

__all__ = [
    "create_access_token",
    "create_token_response",
    "decode_token",
    "get_current_user_data",
    "get_optional_user_data",
    "get_user_with_claim",
]
