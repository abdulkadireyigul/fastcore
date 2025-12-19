"""
Security module root.

ARCHITECTURE CHANGE
-------------------------
To support both Integer (Legacy) and UUID (Modern) token models,
this root module NO LONGER exports token-specific implementations.

REASON:
Exporting `TokenRepository` or `create_access_token` here would force-load
the Legacy (Integer) models, causing conflicts when the application wants
to use UUID models.

USAGE:
- For Password Utils: You can still import from here.
- For Token/Auth Logic: Import directly from the specific submodule.
  - Legacy: `from fastcore.security.tokens.service import ...`
  - UUID:   `from fastcore.security.tokens.uuid.service import ...`
"""

# --- SAFE IMPORTS (No DB Model Dependency) ---
from fastcore.security.password import get_password_hash, verify_password
from fastcore.security.users import (
    AuthenticationError,
    BaseUserAuthentication,
    UserAuthentication,
)

# --- UNSAFE IMPORTS (Commented Out to Prevent Conflict) ---

# from fastcore.security.dependencies import (
#     get_current_user_dependency,
#     get_refresh_token_data,
#     get_token_data,
#     refresh_token,
# )

# from fastcore.security.manager import get_security_status, setup_security

# from fastcore.security.tokens.types import TokenType
# from fastcore.security.tokens.repository import TokenRepository
# from fastcore.security.tokens.service import (
#     create_access_token,
#     create_refresh_token,
#     create_token_pair,
#     decode_token,
#     refresh_access_token,
#     revoke_token,
#     validate_token,
# )
# from fastcore.security.tokens.utils import encode_jwt, validate_jwt_stateless

__all__ = [
    # Safe Utilities
    "get_password_hash",
    "verify_password",
    "UserAuthentication",
    "BaseUserAuthentication",
    "AuthenticationError",
    # REMOVED from __all__ to prevent accidental usage:
    # "create_access_token", "TokenRepository", "setup_security", etc...
]
