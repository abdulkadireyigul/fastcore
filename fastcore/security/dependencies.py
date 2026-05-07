"""
Legacy Security Dependencies Module (Integer-based).

This module initializes the security dependencies for the Legacy (Integer-based)
token system. It uses the `BaseSecurityDependencies` factory, configuring it
with the Legacy service implementation and an integer-based ID converter.

ARCHITECTURE NOTE
-------------------------
This module is intended for applications using the legacy `tokens` table
with Integer IDs. If you are building a new feature or using the UUID system,
please use `fastcore.security.tokens.uuid.dependencies` instead.
"""

from typing import Any

# Import the Legacy service implementation
# (This implicitly loads the Legacy Integer Model, which is expected here)
import fastcore.security.tokens.service as legacy_service
from fastcore.errors.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    RevokedTokenError,
)

# Import the generic base class
from fastcore.security.base_dependencies import BaseSecurityDependencies

# from fastcore.security.tokens.service import (
#     refresh_access_token,
#     revoke_token,
#     validate_token,
# )

# --- Configuration ---


def _int_id_converter(user_id: Any) -> int:
    """
    Converts the token subject (user_id) to an integer.

    The legacy system relies on Integer Primary Keys for users.
    JWT 'sub' claims are strings, so we must cast them back to int.
    """
    return int(user_id)


# --- Initialization ---

# Create an instance of the dependencies factory injected with:
# 1. The Legacy Service module (handling logic for Integer tokens)
# 2. The Integer ID converter (handling type compatibility)
_deps = BaseSecurityDependencies(
    service_module=legacy_service, id_converter=_int_id_converter
)


# --- Public Exports ---
# We expose the bound methods directly for use in FastAPI `Depends()`.

# 1. OAuth2 Scheme
oauth2_scheme = _deps.oauth2_scheme

# 2. Token Validation Dependencies
get_token_data = _deps.get_token_data
get_refresh_token_data = _deps.get_refresh_token_data

# 3. User Retrieval Dependency Factory
# When calling this, pass a dependency that returns `UserAuthentication` (Legacy).
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
