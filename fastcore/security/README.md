# Security Module

This module provides stateful authentication and authorization utilities for FastAPI applications, including JWT-based authentication, password hashing, user authentication interfaces, and robust token management.

## Structure

- `dependencies.py`: FastAPI dependencies for extracting, validating, and refreshing tokens, and for retrieving the current user.
- `exceptions.py`: Custom exception classes for token and authentication errors.
- `manager.py`: Security module setup and status management for FastAPI apps.
- `password.py`: Password hashing and verification utilities using bcrypt.
- `users.py`: Protocols and base classes for user authentication, supporting custom user models.
- `tokens/`: Subpackage for all token-related logic:
  - `models.py`: Token and TokenType SQLAlchemy models.
  - `repository.py`: TokenRepository for database operations on tokens.
  - `service.py`: Business logic for token creation, validation, revocation, and refresh.
  - `utils.py`: Stateless JWT helpers (encode, decode, stateless validation).

## Main Exports

All main security functions, models, helpers, and exceptions are re-exported from `security/__init__.py` for easy access:

- Token management: `create_access_token`, `create_refresh_token`, `create_token_pair`, `validate_token`, `refresh_access_token`, `revoke_token`, `decode_token`, `encode_jwt`, `validate_jwt_stateless`, `TokenRepository`, `TokenType`
- Password utilities: `get_password_hash`, `verify_password`
- User authentication: `UserAuthentication`, `BaseUserAuthentication`, `AuthenticationError`
- FastAPI dependencies: `get_token_data`, `get_current_user_dependency`, `get_refresh_token_data`, `refresh_token`
- Security setup: `setup_security`, `get_security_status`
- Exceptions: `InvalidTokenError`, `ExpiredTokenError`, `RevokedTokenError`, `InvalidCredentialsError`

## Usage Example

```python
from fastcore.security import (
    create_access_token, validate_token, get_password_hash, verify_password,
    get_token_data, get_current_user_dependency, setup_security
)

# Hash a password
hashed = get_password_hash('mysecret')

# Verify a password
is_valid = verify_password('mysecret', hashed)

# Create a JWT access token
access_token = await create_access_token({"sub": user_id}, session)

# Validate a token (stateful)
payload = await validate_token(access_token, session)

# Use FastAPI dependencies in your routes
from fastapi import Depends

@app.get("/me")
async def get_me(token_data=Depends(get_token_data)):
    return token_data
```

## User Authentication Example

Implement a custom user authentication class using `BaseUserAuthentication`:

```python
from fastcore.db import BaseRepository
from fastcore.security.users import BaseUserAuthentication
from fastcore.security.password import verify_password
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User

class UserRepository(BaseRepository[User]):
    def __init__(self, session):
        """
        Initialize the UserRepository with a database session.

        Args:
            session: The database session to use for operations.
        """
        super().__init__(User, session)
    # Implement other methods as needed
    pass

class AuthService(BaseUserAuthentication[User]):
    def __init__(self, session):
        self.repo = UserRepository(session)

    # --- For fastcore security module (Must to use it) ---
    async def authenticate(self, credentials) -> User | None:
        """
        Authenticate a user with username and password.

        Args:
            credentials (dict): Dictionary containing 'username' and 'password'.

        Returns:
            User | None: The authenticated user object if successful, None otherwise.
        """
        user = await self.repo.get_by_username(credentials["username"])
        if user and verify_password(credentials["password"], user.hashed_password):
            return user
        return None

    async def get_user_by_id(self, user_id) -> User:
        """
        Get a user by their ID.

        Args:
            user_id (int): The user's unique identifier.

        Returns:
            User: The user object.
        """
        return await self.repo.get_by_id(user_id)

    def get_user_id(self, user) -> int:
        """
        Extract the user ID from a user object.

        Args:
            user (User): The user object.

        Returns:
            int: The user's ID.
        """
        return user.id
```

> **Note:** You must provide a valid database session to your authentication handler (see above).

## Using get_current_user_dependency

Use your authentication handler with FastAPI dependencies. The handler must be properly initialized before use:

```python
from fastapi import Depends, APIRouter
from fastcore.db.manager import get_db
from fastcore.security.dependencies import get_current_user_dependency
from .service import AuthService

router = APIRouter()

def get_auth_service(session=Depends(get_db)):
    """
    Dependency to provide an AuthService instance with a database session.

    Args:
        session: The database session dependency.

    Returns:
        AuthService: An instance of the AuthService class.
    """
    return AuthService(session)

get_current_user = get_current_user_dependency(get_auth_service)

@router.get("/profile")
async def profile(user=Depends(get_current_user)):
    return {"user_id": user.id, "username": user.username}
```

## Refresh Token and Logout Usage

```python
from fastapi import Depends, APIRouter
from fastcore.security.dependencies import get_refresh_token_data, refresh_token, logout_user

router = APIRouter()

@router.post("/refresh")
async def refresh_access_token(token_data=Depends(get_refresh_token_data)):
    # You can also use refresh_token dependency directly
    ...

@router.post("/logout")
async def logout(result=Depends(logout_user)):
    return result
```

## Limitations

- Only password-based JWT authentication is included by default
- No OAuth2 authorization code, implicit, or client credentials flows
- No social login (Google, Facebook, etc.)
- No multi-factor authentication
- No user registration or management flows (only protocols/interfaces)
- No advanced RBAC or permission system
- No API key support
- Stateless JWT blacklisting/revocation requires stateful DB tracking

## Notes
- All token-related logic is now under the `tokens/` subpackage for maintainability and clarity.
- All public API is accessible from the root `security` module for convenience.
- See each submodule for more detailed documentation and usage.