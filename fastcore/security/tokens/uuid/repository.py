"""
UUID Token Repository Module.

This module implements the repository pattern for UUID-based Token entities.
It acts as a concrete implementation that bridges the generic database capabilities
of `BaseRepository` with the specialized token logic provided by `TokenRepositoryMixin`.

This design ensures that all database operations for UUID tokens are centralized,
type-safe, and consistent with the rest of the application.
"""

from fastcore.db.repository import BaseRepository
from fastcore.security.tokens.mixins import TokenRepositoryMixin

from .models import UUIDToken


class UUIDTokenRepository(BaseRepository[UUIDToken], TokenRepositoryMixin[UUIDToken]):
    """
    Repository for handling UUIDToken database operations.

    This class combines two powerful components:
    1. `BaseRepository`: Provides standard CRUD (Create, Read, Update, Delete) methods
       common to all entities in the system.
    2. `TokenRepositoryMixin`: Injects specialized business logic for tokens,
       such as `revoke_token_for_user`, `get_by_token_id`, and `revoke_all_for_user`.

    By inheriting from both, this class becomes a fully functional repository
    tailored for `UUIDToken` models without writing repetitive code.
    """

    pass
