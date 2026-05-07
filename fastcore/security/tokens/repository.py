"""
Legacy Token Repository Module.

This module implements the repository pattern for Integer-based Token entities.
It serves as the backward-compatible persistence layer for systems that rely on
Integer user IDs.

By inheriting from `TokenRepositoryMixin`, it shares the exact same business logic
and query structure as the modern UUID implementation, ensuring feature parity
while maintaining legacy support.
"""

from fastcore.db.repository import BaseRepository
from fastcore.security.tokens.mixins import TokenRepositoryMixin
from fastcore.security.tokens.models import Token


class TokenRepository(BaseRepository[Token], TokenRepositoryMixin[Token]):
    """
    Legacy Repository for handling Integer-based Token database operations.

    This class provides the concrete implementation for systems using standard
    `Token` models (with Integer user_ids).

    Inheritance:
    - BaseRepository: Provides standard CRUD (Create, Read, Update, Delete).
    - TokenRepositoryMixin: Injects specialized token logic (revocation, validity checks).
    """

    pass
