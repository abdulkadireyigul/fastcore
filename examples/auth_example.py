"""
Authentication and authorization example using FastCore.

This example demonstrates how to use FastCore's security features to implement
authentication and authorization in a FastAPI application.
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from fastcore.config.base import Environment
from fastcore.factory import create_app
from fastcore.security import (
    APIKey,
    JWTAuth,
    Permission,
    Role,
    RolePermission,
    User,
    get_api_key,
    get_current_active_user,
    get_current_superuser,
    get_current_user,
    get_password_hash,
    require_permissions,
    verify_password,
)

# -----------------------------------------------------------------------------
# Application setup
# -----------------------------------------------------------------------------

# Create a FastAPI app
app = create_app(
    env=Environment.DEVELOPMENT,
    title="FastCore Auth Example",
    description="Example of authentication and authorization with FastCore",
    enable_cors=True,
    enable_error_handlers=True,
)

# -----------------------------------------------------------------------------
# User database simulation
# -----------------------------------------------------------------------------


# In a real application, you would use a database to store users
class UserDB(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    hashed_password: str
    roles: List[str] = []


# Simulated user database
fake_users_db: Dict[str, UserDB] = {
    "johndoe": UserDB(
        id="user1",
        username="johndoe",
        email="johndoe@example.com",
        full_name="John Doe",
        disabled=False,
        hashed_password=get_password_hash("secret"),
        roles=["user"],
    ),
    "alice": UserDB(
        id="user2",
        username="alice",
        email="alice@example.com",
        full_name="Alice Wonderland",
        disabled=False,
        hashed_password=get_password_hash("password"),
        roles=["user", "editor"],
    ),
    "admin": UserDB(
        id="user3",
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        disabled=False,
        hashed_password=get_password_hash("admin"),
        roles=["admin", "superuser"],
    ),
}

# -----------------------------------------------------------------------------
# Role and permission management
# -----------------------------------------------------------------------------

# Create role permission manager
role_permission_manager = RolePermission()

# Define permissions
USER_READ = Permission("users", "read")
USER_WRITE = Permission("users", "write")
USER_DELETE = Permission("users", "delete")
ITEM_READ = Permission("items", "read")
ITEM_WRITE = Permission("items", "write")
ITEM_DELETE = Permission("items", "delete")

# Define roles and their permissions
role_permission_manager.add_role(
    "user",
    [
        ITEM_READ.name,
    ],
)

role_permission_manager.add_role(
    "editor",
    [
        ITEM_READ.name,
        ITEM_WRITE.name,
    ],
)

role_permission_manager.add_role(
    "admin",
    [
        USER_READ.name,
        USER_WRITE.name,
        USER_DELETE.name,
        ITEM_READ.name,
        ITEM_WRITE.name,
        ITEM_DELETE.name,
    ],
)

role_permission_manager.add_role("superuser", ["*:*"])  # All permissions

# -----------------------------------------------------------------------------
# Authentication setup
# -----------------------------------------------------------------------------

# Create JWT authentication handler
jwt_auth = JWTAuth()


# Configure user retriever function for use with security dependencies
def get_user_by_id(user_id: str) -> User:
    """Get a user by ID from the fake database."""
    for db_user in fake_users_db.values():
        if db_user.id == user_id:
            # Get permissions for user roles
            permissions = role_permission_manager.get_user_permissions(db_user.roles)

            # Convert to User model
            return User(
                id=db_user.id,
                username=db_user.username,
                email=db_user.email,
                full_name=db_user.full_name,
                disabled=db_user.disabled,
                roles=db_user.roles,
                permissions=permissions,
            )

    raise HTTPException(status_code=404, detail="User not found")


# Configure security dependencies
from fastcore.security.dependencies import configure_jwt_auth, configure_user_retriever

configure_jwt_auth(jwt_auth)
configure_user_retriever(get_user_by_id)

# -----------------------------------------------------------------------------
# Authentication endpoints
# -----------------------------------------------------------------------------


@app.post("/auth/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token endpoint.

    This endpoint authenticates a user and returns an access token.
    """
    # Authenticate user
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is disabled
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Create token with user info
    token_response = jwt_auth.create_token_response(
        subject=user.id,
        additional_claims={
            "username": user.username,
            "email": user.email,
            "role": user.roles[0] if user.roles else None,
            "permissions": role_permission_manager.get_user_permissions(user.roles),
        },
        include_refresh_token=True,
    )

    return token_response


# -----------------------------------------------------------------------------
# API endpoints with different permission requirements
# -----------------------------------------------------------------------------


@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get the current authenticated user."""
    return current_user


@app.get("/users/", dependencies=[Depends(require_permissions(["users:read"]))])
async def read_users():
    """List all users (requires users:read permission)."""
    users = []
    for username, db_user in fake_users_db.items():
        users.append(
            {
                "id": db_user.id,
                "username": db_user.username,
                "email": db_user.email,
                "roles": db_user.roles,
            }
        )
    return users


@app.get("/admin/", dependencies=[Depends(get_current_superuser)])
async def read_admin():
    """Admin-only endpoint."""
    return {"message": "Admin access granted"}


@app.get("/items/")
async def read_items(user: User = Depends(get_current_active_user)):
    """List items (requires authentication)."""
    # Check permission using role permission manager
    has_permission = role_permission_manager.check_permission(user.roles, "items:read")

    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return [
        {"id": 1, "name": "Item 1", "owner": "johndoe"},
        {"id": 2, "name": "Item 2", "owner": "alice"},
    ]


@app.post("/items/", dependencies=[Depends(require_permissions(["items:write"]))])
async def create_item():
    """Create an item (requires items:write permission)."""
    return {"message": "Item created"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
