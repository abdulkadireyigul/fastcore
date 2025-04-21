# Security Module

A stateful JWT authentication module for FastAPI applications, providing token management, password utilities, and FastAPI dependencies for route protection.

## Features

- Stateful JWT authentication with database-backed token tracking
- Refresh token functionality for extended sessions
- Password hashing and verification using bcrypt
- Token revocation capabilities (logout functionality)
- Multi-device logout support (revoke all tokens)
- Audience validation to prevent token misuse across applications
- Cookie-based token storage for enhanced security
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

Use the `get_current_user` dependency to protect routes:

```python
from fastapi import APIRouter, Depends
from fastcore.security import get_current_user

router = APIRouter()

@router.get("/me")
async def get_user_info(current_user = Depends(get_current_user)):
    return current_user
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

### Advanced Authentication Patterns

#### Cookie-Based Refresh Tokens

For enhanced security, store refresh tokens in HTTP-only cookies:

```python
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from fastcore.db import get_db
from fastcore.security.tokens import create_token_pair
from fastcore.security.dependencies import get_refresh_token_from_cookie, refresh_token

router = APIRouter()

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
    response: Response = None
):
    # Authenticate user (implementation not shown)
    user = await authenticate_user(form_data.username, form_data.password, session)
    
    # Create tokens
    tokens = await create_token_pair(
        {"sub": user.id}, 
        session,
        audience="your-app-audience",  # Specify the audience for enhanced security
    )
    
    # Return access token in response body
    content = {"access_token": tokens.access_token, "token_type": "bearer"}
    
    # Set refresh token as HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=True,  # For HTTPS only
        samesite="strict",
        max_age=60*60*24*7,  # 7 days in seconds
    )
    
    return content

@router.post("/refresh")
async def refresh_access_token(
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    session: AsyncSession = Depends(get_db)
):
    # Use refresh token from cookie to get new access token
    new_token = await refresh_token(refresh_token, session)
    return {"access_token": new_token, "token_type": "bearer"}
```

#### Logout and Device Management

Implement secure logout functionality:

```python
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.db import get_db
from fastcore.security.dependencies import (
    logout_user, 
    logout_all_devices, 
    get_current_user_dependency
)
from fastcore.security.users import UserAuthentication

# Create custom user dependency
get_current_user = get_current_user_dependency(YourUserAuthenticationClass())

router = APIRouter()

@router.post("/logout")
async def user_logout(
    response: Response,
    result = Depends(logout_user)
):
    """Logout the current user from the current device."""
    return result

@router.post("/logout-all")
async def logout_everywhere(
    response: Response,
    current_user = Depends(get_current_user),
    result = Depends(logout_all_devices)
):
    """Logout the current user from all devices."""
    return result

@router.post("/revoke-suspicious")
async def revoke_suspicious_sessions(
    current_user = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Example of a security feature that revokes all tokens
    except the current one when suspicious activity is detected.
    """
    # Get current token's ID
    token_id = current_user.token_id  # Assuming you store this in the user context
    
    # Revoke all tokens except current one
    await revoke_all_user_tokens(
        user_id=current_user.id,
        session=session,
        exclude_token_id=token_id
    )
    
    return {"message": "All other sessions have been revoked"}
```

## Security Best Practices

### JWT Secret Management

The default `JWT_SECRET_KEY` is intentionally insecure for development. For production:

```bash
# Generate a strong random key (in a terminal)
python -c "import secrets; print(secrets.token_hex(32))"
```

Set this key using one of these methods:
- Environment variable: `JWT_SECRET_KEY=your-generated-secret`
- Docker secret: Mount as `/run/secrets/jwt_secret_key`
- Kubernetes secret: Mount and reference in environment
- AWS Secret Manager/Azure Key Vault (for cloud deployments)

**Important:** Never commit JWT secrets to source control or expose them in client-side code.

### Production Hardening

1. **Token Security**
   - Keep token expiration times short (30 min for access tokens is reasonable)
   - Implement regular key rotation (e.g., monthly)
   - Enable automatic revocation on password change/suspicious activity

2. **Transport Security**
   - Always use HTTPS in production
   - Set cookies with `secure=True` and `httponly=True` flags
   - Consider implementing CSRF protection for cookie-based auth

3. **Database Protection**
   - Ensure proper indexes on token tables for performance
   - Implement token cleanup through scheduled tasks (use the upcoming tasks module)
   - Consider sharding or partitioning for high-volume applications

4. **Monitoring and Alerting**
   - Log authentication failures and token validation errors
   - Set up alerts for unusual patterns (many failed attempts, token reuse)
   - Implement audit logging for security-critical operations

### JWT Token Security

#### Audience and Issuer Validation

Always specify audience and issuer claims in production for enhanced security:

```python
# When creating tokens
tokens = await create_token_pair(
    data={"sub": user_id},
    session=session,
    audience="your-app-id",  # App-specific identifier
    issuer="your-auth-service"  # Who created the token
)
```

This prevents token misuse across different applications or environments.

### Token Lifecycle Management

1. **Short-lived Access Tokens**
   - Keep access tokens short-lived (15-30 minutes)
   - Use refresh tokens for extended sessions
   
2. **Token Revocation**
   - Revoke tokens on password change
   - Implement an endpoint to view and revoke active sessions
   - Consider automatic token revocation for suspicious activities (location change, unusual user agent)

3. **Token Storage**
   - Store access tokens in memory (never in localStorage)
   - Store refresh tokens in HTTP-only cookies
   - Clear tokens properly on logout

### Protecting Against Common Attacks

1. **JWT-Specific Attacks**
   - Use proper algorithms (HS256, RS256) and avoid vulnerable algorithms (none, HS256 with empty secret)
   - Validate all claims (exp, nbf, iss, aud)
   - Properly validate signatures

2. **Cross-Site Request Forgery (CSRF)**
   - For cookie-based tokens, implement CSRF tokens or use SameSite=Strict
   - Use the double submit cookie pattern when appropriate

3. **Token Leakage**
   - Don't include tokens in URLs
   - Set proper CORS policies
   - Use HTTPS everywhere in production
   - Implement token binding where possible

### Implementation Patterns

#### Logout Pattern

For complete logout security, implement both client and server-side logout:

```python
@router.post("/complete-logout")
async def complete_logout(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Revoke all user tokens (logout from all devices)
    await revoke_all_tokens(current_user.id, session)
    
    # Client-side: Also clear cookies in the response
    response = JSONResponse(content={"detail": "Successfully logged out from all devices"})
    response.delete_cookie("refresh_token")
    return response
```

#### Refresh Token Pattern

Store refresh tokens in HTTP-only cookies for better security:

```python
@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    # Authentication logic...
    tokens = await create_token_pair({"sub": user.id}, session)
    
    # Return access token in response body
    content = {"access_token": tokens["access_token"], "token_type": "bearer"}
    
    # Set refresh token as HTTP-only cookie
    response = JSONResponse(content=content)
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # For HTTPS only
        samesite="strict",
        max_age=60*60*24*7,  # 7 days in seconds
    )
    return response
```

### Implementation Patterns for Specific Use Cases

#### Single Sign-On (SSO)

If implementing SSO with this module:

```python
# Create tokens with additional claims for SSO
tokens = await create_token_pair(
    data={
        "sub": user.id,
        "email": user.email,
        "roles": user.roles,
        "org_id": user.organization_id,
    },
    session=session,
    audience="your-app-audience",
    issuer="your-sso-service"
)
```

#### Microservices Authentication

For service-to-service authentication:

```python
# Create a service token with specific audience
service_token = await create_access_token(
    data={"sub": "service-name", "service": True},
    session=session,
    audience="target-service-name",
    issuer="calling-service-name",
    expires_in=timedelta(hours=1)  # Longer-lived for services
)
```

#### Mobile API Authentication

For mobile apps, consider implementing device-specific tokens:

```python
# Create tokens with device info
tokens = await create_token_pair(
    data={
        "sub": user.id,
        "device_id": device_id,
        "device_type": "ios|android",
    },
    session=session,
    audience="mobile-app",
)

# Later, validate device consistency
@router.get("/sensitive-data")
async def get_sensitive_data(
    token_data: dict = Depends(get_token_data),
    device_id: str = Header(None)
):
    # Verify device ID matches the one in token
    if token_data.get("device_id") != device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device mismatch detected"
        )
    # Continue with the handler...
```

## Advanced Configuration

### Custom Claims Validation

You can implement custom validators for specific use cases:

```python
from fastcore.security.tokens import create_token_validator

# Create custom validation logic
def validate_permissions(payload: dict) -> bool:
    required_permissions = ["read:data", "write:data"]
    user_permissions = payload.get("permissions", [])
    return all(perm in user_permissions for perm in required_permissions)

# Create the validator
permission_validator = create_token_validator(validate_permissions)

# Use in routes
@router.get("/protected-resource")
async def get_protected_resource(
    token_data: dict = Depends(get_token_data),
    _: bool = Depends(permission_validator)
):
    # If we get here, permissions are valid
    return {"data": "protected resource content"}
```

### Rate Limiting for Authentication

Implement rate limiting for login and token refresh to prevent brute force attacks:

```python
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastcore.cache import RateLimiter  # Hypothetical rate limiter
from datetime import timedelta

rate_limiter = RateLimiter(max_attempts=5, period=timedelta(minutes=15))

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    # Rate limit by IP address
    client_ip = request.client.host
    if not await rate_limiter.check(f"login:{client_ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later."
        )
    
    # Continue with login logic...
```

## Error Handling

The security module includes specialized exceptions for different security-related errors:

- `InvalidTokenError`: When a token is malformed or invalid
- `ExpiredTokenError`: When a token has expired
- `RevokedTokenError`: When a token has been revoked
- `InvalidCredentialsError`: When authentication credentials are invalid

These exceptions are designed to work with FastAPI's exception handling and can be caught and converted to appropriate HTTP responses.

## Debugging and Troubleshooting

### Common Issues

1. **Token Validation Failures**
   - Check clock synchronization between servers
   - Verify that audience and issuer settings match
   - Ensure the correct algorithm is being used

2. **Database Performance**
   - Implement periodic cleanup of expired tokens
   - Add proper indexes to the token table
   - Consider sharding for high-volume applications

3. **Token Leakage**
   - Implement token tracking and analytics
   - Monitor for unusual token usage patterns
   - Consider adding IP or device binding to tokens

### Logging and Monitoring

Enable detailed logging for authentication issues:

```python
# In your application startup
import logging
logging.getLogger("fastcore.security").setLevel(logging.DEBUG)

# In production, track authentication metrics
from fastcore.monitoring import metrics  # Hypothetical metrics module

@router.post("/login")
async def login():
    # Track login attempts
    metrics.increment("auth.login.attempt")
    
    try:
        # Login logic
        metrics.increment("auth.login.success")
    except Exception:
        metrics.increment("auth.login.failure")
        raise
```