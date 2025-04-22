# Security Module

Authentication and authorization utilities for FastAPI applications, with JWT token support and password hashing.

## Features

- JWT-based authentication with access and refresh tokens
- Secure password hashing with bcrypt
- Token revocation support
- User authentication workflow
- FastAPI dependencies for protected routes
- Role-based access control

## Installation

Install the required dependencies:

```bash
pip install pyjwt passlib[bcrypt]
```

## Configuration

Configure security settings through environment variables or settings class:

```python
from fastcore.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    # Security settings
    SECRET_KEY: str = "your-secret-key-here"  # Change in production!
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

Common environment variables:
- `SECRET_KEY`: Secret key used for token signing
- `JWT_ALGORITHM`: Algorithm used for JWT (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token lifetime in minutes
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token lifetime in days

## Usage

### Password Hashing

Securely hash and verify passwords:

```python
from fastcore.security import get_password_hash, verify_password

# Hash a password
hashed_password = get_password_hash("user-password")

# Verify a password against a hash
is_valid = verify_password("user-password", hashed_password)
```

### Token Generation

Create JWT tokens for authentication:

```python
from fastcore.security import create_access_token, create_refresh_token

# Generate tokens for a user
user_data = {"sub": "user@example.com", "user_id": 123}
access_token = create_access_token(data=user_data)
refresh_token = create_refresh_token(data=user_data)

# Or create both tokens at once
tokens = create_token_pair(data=user_data)
```

### Protected Routes

Secure your API endpoints:

```python
from fastapi import APIRouter, Depends
from fastcore.security import get_current_user
from pydantic import BaseModel

class User(BaseModel):
    id: int
    email: str
    is_active: bool

router = APIRouter()

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### Token Refresh

Implement token refresh functionality:

```python
from fastapi import APIRouter, Depends
from fastcore.security import refresh_token, get_refresh_token_data

router = APIRouter()

@router.post("/refresh")
async def refresh_access_token(token_data: dict = Depends(get_refresh_token_data)):
    # This will validate the refresh token and create a new access token
    new_access_token = refresh_access_token(token_data)
    return {"access_token": new_access_token, "token_type": "bearer"}
```

### Custom Authentication

Extend the base authentication class:

```python
from fastcore.security import BaseUserAuthentication
from fastcore.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

class DatabaseUserAuthentication(BaseUserAuthentication):
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def authenticate_user(self, username: str, password: str):
        # Query user from database
        user = await get_user_by_username(self.db, username)
        if not user:
            return None
            
        # Verify password
        if not verify_password(password, user.hashed_password):
            return None
            
        return user

# Use in a login endpoint
@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    auth = DatabaseUserAuthentication(db)
    user = await auth.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    # Create tokens for the authenticated user
    tokens = create_token_pair({"sub": user.email, "user_id": user.id})
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer"
    }
```

## Integration with Factory

Security features are automatically set up when using the application factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Sets up security based on app settings
```