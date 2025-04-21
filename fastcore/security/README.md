# Security Module

A stateful JWT authentication module for FastAPI applications, providing token management, password utilities, and FastAPI dependencies for route protection.

## Features

- Stateful JWT authentication with database-backed token tracking
- Refresh token functionality for extended sessions
- Password hashing and verification using bcrypt
- Token revocation capabilities (logout functionality)
- Audience validation to prevent token misuse across applications
- FastAPI dependencies for protecting routes
- Consistent error handling for security-related exceptions

## Installation

The security module requires the following dependencies:

```bash
pip install pyjwt passlib[bcrypt]
```

## Configuration

Configure security settings via environment variables or programmatically in your settings class:

```env
JWT_SECRET_KEY=your-secure-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_AUDIENCE=your-application-id
JWT_ISSUER=your-authentication-server
```

Fields on `BaseAppSettings`:

- `JWT_SECRET_KEY`: Secret key for signing JWT tokens (default: `supersecret` - **change in production**)
- `JWT_ALGORITHM`: Algorithm used for token signing (default: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Access token lifetime in minutes (default: `30`)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token lifetime in days (default: `7`)
- `JWT_AUDIENCE`: Audience claim for token validation (default: `None` - **specify in production**)
- `JWT_ISSUER`: Issuer claim for token validation (default: `None` - **specify in production**)

## Usage

### Factory Integration

In your application factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # This will automatically set up the security module
```

### Basic Authentication Flow

Create a login endpoint that issues tokens:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db import get_session
from fastcore.security import create_token_pair, get_password_hash, verify_password

router = APIRouter()

# Example function to get a user from the database
async def get_user_by_username(username: str, session: AsyncSession):
    # This would be your actual database lookup
    # For example purposes only:
    if username == "testuser":
        return {"id": "user1", "username": "testuser", "hashed_password": get_password_hash("password")}
    return None

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_username(form_data.username, session)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access and refresh tokens
    tokens = await create_token_pair({"sub": user["id"]}, session)
    return tokens  # Returns access_token, refresh_token, and token_type
```

### Protecting Routes

Use the `get_token_data` or `get_current_user_dependency` dependency to protect routes and extract user information from the token:

```python
from fastapi import APIRouter, Depends
from fastcore.security import get_token_data

router = APIRouter()

@router.get("/me")
async def get_user_info(token_data = Depends(get_token_data)):
    return token_data  # Contains claims like user_id (sub), etc.
```

### Token Refresh

Implement a refresh endpoint to get a new access token:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db import get_session
from fastcore.security import refresh_access_token
from fastcore.security.exceptions import ExpiredTokenError, InvalidTokenError, RevokedTokenError

router = APIRouter()

@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    session: AsyncSession = Depends(get_session)
):
    try:
        new_access_token = await refresh_access_token(refresh_token, session)
        return {"access_token": new_access_token, "token_type": "bearer"}
    except (InvalidTokenError, ExpiredTokenError, RevokedTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### Logout

Implement a logout endpoint to revoke tokens:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db import get_session
from fastcore.security import revoke_token
from fastcore.security.exceptions import InvalidTokenError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
router = APIRouter()

@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
):
    try:
        await revoke_token(token, session)
        return {"detail": "Successfully logged out"}
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
```

## Error Handling

The security module includes specialized exceptions for different security-related errors:

- `InvalidTokenError`: When a token is malformed or invalid
- `ExpiredTokenError`: When a token has expired
- `RevokedTokenError`: When a token has been revoked
- `InvalidCredentialsError`: When authentication credentials are invalid

These exceptions are designed to work with FastAPI's exception handling and can be caught and converted to appropriate HTTP responses.

## Security Best Practices

- Use a strong, random `JWT_SECRET_KEY` in production (never commit secrets to source control).
- Keep access tokens short-lived (15-30 minutes) and use refresh tokens for extended sessions.
- Always use HTTPS in production and set cookies with `secure=True` and `httponly=True` if using cookies.
- Validate all claims (exp, nbf, iss, aud) and use audience/issuer checks in production.
- Revoke tokens on password change or suspicious activity.
- Log authentication failures and monitor for unusual patterns.

---

> **Note:** Advanced features (multi-device logout, cookie-based refresh, SSO, rate limiting, etc.) and related functions are optional/for advanced usage and are not enabled by default in the main module. For such advanced integrations, you should update your code and documentation accordingly.