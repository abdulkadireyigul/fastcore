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