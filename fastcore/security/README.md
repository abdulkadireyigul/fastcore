# Security Module

This module provides stateful authentication and authorization utilities for FastAPI applications, including JWT-based authentication, password hashing, user authentication interfaces, and robust token management with support for both **header-based** and **cookie-based** authentication.

It is designed to be flexible, supporting both **Legacy (Integer ID)** and **Modern (UUID)** user identification systems.

## Structure

- `dependencies.py`: FastAPI dependencies for extracting, validating, and refreshing tokens, and for retrieving the current user. Includes both header-based and cookie-based authentication dependencies.
- `exceptions.py`: Custom exception classes for token and authentication errors.
- `manager.py`: Security module setup and status management for FastAPI apps.
- `password.py`: Password hashing and verification utilities using bcrypt.
- `users.py`: Protocols and base classes for user authentication (Integer & UUID).
- `tokens/`: Subpackage for all token-related logic:
  - `uuid/`: **NEW** Specialized subpackage for UUID-based token operations (Service, Repository, Models).
  - `models.py`: Legacy Token and TokenType SQLAlchemy models.
  - `repository.py`: Legacy TokenRepository for database operations on tokens.
  - `service.py`: Business logic for token creation, validation, revocation, and refresh.
  - `utils.py`: Stateless JWT helpers (encode, decode, stateless validation).

## Main Exports

All main security functions, models, helpers, and exceptions are re-exported from `security/__init__.py` for easy access:

- Token management: `create_access_token`, `create_refresh_token`, `create_token_pair`, `validate_token`, `refresh_access_token`, `revoke_token`, `decode_token`, `encode_jwt`, `validate_jwt_stateless`, `TokenRepository`, `TokenType`
- Password utilities: `get_password_hash`, `verify_password`
- User authentication: `UserAuthentication`, `BaseUserAuthentication`, `BaseUUIDUserAuthentication`, `AuthenticationError`
- FastAPI dependencies (Header-based): `get_token_data`, `get_current_user_dependency`, `get_refresh_token_data`, `refresh_token`, `logout_user`
- FastAPI dependencies (Cookie-based): `get_token_data_from_cookie`, `get_current_user_from_cookie_dependency`, `logout_user_cookie`, `set_auth_cookies`
- Security setup: `setup_security`, `get_security_status`
- Exceptions: `InvalidTokenError`, `ExpiredTokenError`, `RevokedTokenError`, `InvalidCredentialsError`

## Authentication Methods

The module supports two authentication methods:

### 1. Header-based Authentication (Bearer Token)

Traditional JWT authentication using the `Authorization: Bearer <token>` header.

### 2. Cookie-based Authentication (HTTP-only Cookies)

Secure authentication using HTTP-only cookies, ideal for web applications to prevent XSS attacks.

## Usage Examples

### Basic Token Operations

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

### Header-based Authentication

```python
from fastapi import Depends, APIRouter
from fastcore.security.dependencies import get_current_user_dependency

router = APIRouter()

def get_auth_service(session=Depends(get_db)):
    return AuthService(session)

get_current_user = get_current_user_dependency(get_auth_service)

@router.get("/profile")
async def profile(user=Depends(get_current_user)):
    return {"user_id": user.id, "username": user.username}
```

### Cookie-based Authentication

#### Setting Authentication Cookies

```python
from fastapi import APIRouter, Response, Depends
from fastcore.security.dependencies import set_auth_cookies
from fastcore.security import create_token_pair

router = APIRouter()

@router.post("/login")
async def login(
    credentials: LoginCredentials,
    response: Response,
    session=Depends(get_db)
):
    # Authenticate user (your implementation)
    user = await authenticate_user(credentials.username, credentials.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create token pair
    access_token, refresh_token = await create_token_pair(
        {"sub": str(user.id)}, session
    )

    # Set secure HTTP-only cookies
    set_auth_cookies(
        response=response,
        access_token=access_token,
        refresh_token=refresh_token
    )

    return {"message": "Login successful"}
```

#### Using Cookie-based Dependencies

```python
from fastapi import Depends, APIRouter
from fastcore.security.dependencies import (
    get_current_user_from_cookie_dependency,
    get_token_data_from_cookie
)

router = APIRouter()

def get_auth_service(session=Depends(get_db)):
    return AuthService(session)

get_current_user_cookie = get_current_user_from_cookie_dependency(get_auth_service)

@router.get("/profile")
async def profile(user=Depends(get_current_user_cookie)):
    return {"user_id": user.id, "username": user.username}

@router.get("/token-info")
async def token_info(token_data=Depends(get_token_data_from_cookie)):
    return {"user_id": token_data["sub"], "expires": token_data["exp"]}
```

#### Cookie-based Logout

```python
from fastapi import Depends, APIRouter, Response
from fastcore.security.dependencies import logout_user_cookie

router = APIRouter()

@router.post("/logout")
async def logout(result=Depends(logout_user_cookie)):
    return result

# Or manually with response object
@router.post("/logout-manual")
async def logout_manual(
    response: Response,
    result=Depends(logout_user_cookie)
):
    # The logout_user_cookie dependency automatically handles cookie clearing
    # when a Response object is available
    return result
```

## User Authentication Examples

### 1. Legacy Integer-ID Authentication

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

    async def get_user_by_id(self, user_id: int) -> User:
        return await self.repo.get_by_id(user_id)

    def get_user_id(self, user) -> int:
        return user.id

```

### 2. Modern UUID Authentication (New)

For systems using UUIDs, inherit from `BaseUUIDUserAuthentication`. The interface automatically handles UUID-to-String conversions for JWT compatibility.

```python
import uuid
from typing import Union
from fastcore.security.tokens.uuid.users import BaseUUIDUserAuthentication
from .models import UUIDUser

class UUIDAuthService(BaseUUIDUserAuthentication[UUIDUser]):
    def __init__(self, session):
        self.repo = UUIDUserRepository(session)

    async def authenticate(self, credentials) -> UUIDUser | None:
        # Same authentication logic
        ...

    async def get_user_by_id(self, user_id: Union[uuid.UUID, str]) -> UUIDUser:
        """
        Supports both UUID objects and string representations from JWTs.
        """
        return await self.repo.get_by_id(user_id)

    def get_user_id(self, user) -> Union[uuid.UUID, str]:
        return user.id

```

> **Note:** You must provide a valid database session to your authentication handler (see above).

## Cookie Configuration

### Environment Variables

Cookie behavior is controlled by environment variables:

```bash
# Application environment (affects cookie security)
APP_ENV=production  # or "development"

# Token expiration times
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30  # Default: 30 minutes
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7     # Default: 7 days
```

### Cookie Security Features

- **HTTP-only**: Cookies are not accessible via JavaScript (prevents XSS)
- **Secure**: Cookies are only sent over HTTPS in production
- **SameSite=Strict**: Provides CSRF protection
- **Automatic expiration**: Cookies expire based on token lifetime
- **Secure clearing**: Logout properly removes all authentication cookies

## Complete Authentication Flow Examples

### Header-based Flow

```python
from fastapi import FastAPI, Depends, HTTPException
from fastcore.security import setup_security, create_token_pair
from fastcore.security.dependencies import get_current_user_dependency

app = FastAPI()

# Setup security module
await setup_security(app)

def get_auth_service(session=Depends(get_db)):
    return AuthService(session)

get_current_user = get_current_user_dependency(get_auth_service)

@app.post("/login")
async def login(credentials: LoginCredentials, session=Depends(get_db)):
    user = await authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token, refresh_token = await create_token_pair(
        {"sub": str(user.id)}, session
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.get("/protected")
async def protected_route(user=Depends(get_current_user)):
    return {"message": f"Hello {user.username}!"}
```

### Cookie-based Flow

```python
from fastapi import FastAPI, Depends, HTTPException, Response
from fastcore.security import setup_security, create_token_pair
from fastcore.security.dependencies import (
    get_current_user_from_cookie_dependency,
    set_auth_cookies,
    logout_user_cookie
)

app = FastAPI()

# Setup security module
await setup_security(app)

def get_auth_service(session=Depends(get_db)):
    return AuthService(session)

get_current_user_cookie = get_current_user_from_cookie_dependency(get_auth_service)

@app.post("/login")
async def login(
    credentials: LoginCredentials,
    response: Response,
    session=Depends(get_db)
):
    user = await authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token, refresh_token = await create_token_pair(
        {"sub": str(user.id)}, session
    )
    
    # Set secure cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return {"message": "Login successful", "user": {"id": user.id, "username": user.username}}

@app.get("/protected")
async def protected_route(user=Depends(get_current_user_cookie)):
    return {"message": f"Hello {user.username}!"}

@app.post("/logout")
async def logout(result=Depends(logout_user_cookie)):
    return result
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

## Security Best Practices

### Cookie-based Authentication

- Use HTTPS in production (cookies marked as secure)
- HTTP-only cookies prevent XSS attacks
- SameSite=Strict provides CSRF protection
- Automatic cookie expiration based on token lifetime
- Secure logout clears all authentication cookies

### Header-based Authentication

- Use HTTPS to protect tokens in transit
- Store tokens securely on the client side
- Implement proper token refresh logic
- Handle token expiration gracefully

### General Security

- Use strong, randomly generated JWT secrets
- Implement proper password hashing with bcrypt
- Use stateful token validation with database tracking
- Implement token revocation for logout
- Monitor and log authentication events

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
- **UUID Support:** The module now fully supports UUID-based primary keys via the `tokens.uuid` subpackage and `BaseUUIDUserAuthentication` class.
- All public API is accessible from the root `security` module for convenience.
- Cookie-based authentication is ideal for web applications where you control both frontend and backend.
- Header-based authentication is suitable for APIs consumed by mobile apps or third-party clients.
- Both authentication methods can be used simultaneously in the same application.
- See each submodule for more detailed documentation and usage.
