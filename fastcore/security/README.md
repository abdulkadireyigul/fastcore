# Security Module

JWT-based authentication and permission management for FastAPI applications. This module provides tools for password hashing,
JWT token generation/validation, authentication dependencies, and role-based access control.

## Features

- Secure password hashing with bcrypt
- JWT token generation and validation
- FastAPI dependencies for protected routes
- Role-based access control (RBAC)
- Permission and scope-based authorization
- No user model dependencies - works with any user representation

## Configuration

Configure security settings in your `BaseAppSettings` (in `fastcore.config`):

```ini
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Usage

### Password Handling

```python
from fastcore.security import hash_password, verify_password

# Hash a password during user registration
hashed_password = hash_password("user_password")

# Verify during login
is_valid = verify_password("user_password", hashed_password)
```

### Token Generation

```python
from fastapi import Depends, FastAPI
from fastcore.security import create_access_token, create_token_response

app = FastAPI()

@app.post("/token")
async def login(username: str, password: str):
    # Authenticate user (example - replace with your logic)
    if username == "test" and password == "password":
        # Create token with user data
        token_data = {
            "sub": username,  # Required
            "roles": ["admin"],  # For role-based access
            "permissions": ["users:read", "users:write"]  # For direct permission checks
        }
        return create_token_response(token_data)
    else:
        raise UnauthorizedError(message="Invalid credentials")
```

### Protected Routes

```python
from fastapi import Depends
from fastcore.security import get_current_user_data

@app.get("/protected")
async def protected_route(user_data: dict = Depends(get_current_user_data)):
    return {
        "message": f"Hello {user_data['sub']}",
        "data": user_data
    }
```

### Optional Authentication

```python
from typing import Optional
from fastcore.security import get_optional_user_data

@app.get("/items")
async def list_items(user_data: Optional[dict] = Depends(get_optional_user_data)):
    if user_data:
        # User is authenticated
        return {"items": ["secret item 1", "secret item 2"]}
    else:
        # Public access
        return {"items": ["public item 1"]}
```

### Role-Based Access Control

```python
from fastcore.security import role_manager, has_role, has_permission

# Setup your roles during application startup
def setup_roles():
    # Define roles and their permissions
    role_manager.add_role("admin", ["users:*", "products:*"])
    role_manager.add_role("editor", ["users:read", "products:write"])
    role_manager.add_role("viewer", ["users:read", "products:read"])

# Use role-based protection
@app.get("/admin", dependencies=[Depends(has_role("admin"))])
async def admin_panel():
    return {"message": "Admin panel"}

# Use permission-based protection
@app.get("/users", dependencies=[Depends(has_permission("users:read"))])
async def list_users():
    return {"users": ["user1", "user2"]}
```

### Advanced Token Claims

```python
from fastcore.security import get_user_with_claim

# Check for specific claims in token
@app.get("/premium")
async def premium_content(
    user_data: dict = Depends(get_user_with_claim("is_premium", True))
):
    return {"content": "Premium content"}
```

## Working with User Models

This module doesn't impose any specific user model requirements. Instead, it works with any user representation by storing the user identifier in the token's `sub` claim.

### Example with SQLAlchemy User Model

```python
from fastapi import Depends
from fastcore.security import get_current_user_data
from fastcore.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.repositories import UserRepository

@app.get("/me")
async def get_current_user(
    user_data: dict = Depends(get_current_user_data),
    db: AsyncSession = Depends(get_db)
):
    # Extract user ID from token
    user_id = user_data["sub"]
    
    # Fetch the full user from the database
    repo = UserRepository(User, db)
    user = await repo.get_by_id(user_id)
    
    return user
```