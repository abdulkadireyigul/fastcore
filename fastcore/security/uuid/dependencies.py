"""
UUID Security Dependencies Module.

This module initializes the security dependencies specifically for the
UUID-based token system. It utilizes the `BaseSecurityDependencies` factory,
configuring it with the UUID service implementation and a string-based ID converter.

Usage:
    from fastcore.security.tokens.uuid.dependencies import get_current_user_dependency
    from app.modules.auth.dependencies import get_uuid_auth_handler

    get_current_user = get_current_user_dependency(get_uuid_auth_handler)
"""

from typing import Any

# Import the UUID-specific service implementation
# (This avoids importing the Legacy service/models, preventing conflicts)
import fastcore.security.tokens.uuid.service as uuid_service

# Import the generic base class
from fastcore.security.base_dependencies import BaseSecurityDependencies

# --- Configuration ---


def _uuid_id_converter(user_id: Any) -> str:
    """
    Converts the token subject (user_id) to a string.

    Since UUIDs are serialized as strings in JWT 'sub' claims,
    we ensure the ID remains a string for the UUIDUserAuthentication handler.
    """
    return str(user_id)


# --- Initialization ---

# Create an instance of the dependencies factory injected with:
# 1. The UUID Service module (handling logic)
# 2. The String ID converter (handling type compatibility)
_deps = BaseSecurityDependencies(
    service_module=uuid_service, id_converter=_uuid_id_converter
)


# --- Public Exports ---
# We expose the bound methods directly for use in FastAPI `Depends()`.

# 1. OAuth2 Scheme
oauth2_scheme = _deps.oauth2_scheme

# 2. Token Validation Dependencies
get_token_data = _deps.get_token_data
get_refresh_token_data = _deps.get_refresh_token_data

# 3. User Retrieval Dependency Factory
# When calling this, pass a dependency that returns `UUIDUserAuthentication`.
get_current_user_dependency = _deps.get_current_user_dependency

# 4. Token Operations
refresh_token = _deps.refresh_token
logout_user = _deps.logout_user

# 5. Cookie-Based Authentication
get_token_data_from_cookie = _deps.get_token_data_from_cookie
get_current_user_from_cookie_dependency = _deps.get_current_user_from_cookie_dependency
logout_user_cookie = _deps.logout_user_cookie

# 6. Utilities (Static Methods)
set_auth_cookies = _deps.set_auth_cookies
remove_auth_cookies = _deps.remove_auth_cookies
