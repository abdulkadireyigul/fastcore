"""
Legacy Token Package Initialization.

IMPORTANT ARCHITECTURE NOTE!
----------------------------------
This __init__.py file is INTENTIONALLY LEFT EMPTY of logic imports.

Reason:
This package contains the 'Legacy Token (Integer)' implementation.
However, the project also supports 'UUID Tokens' in the `uuid/` subpackage.

If we expose shortcuts here (e.g., `from .service import create_token`),
Python will load the `models.py` (Legacy) immediately upon accessing this package.
This triggers the Conflict Guard if the application is trying to use UUID tokens,
causing "Both models imported" warnings or database schema conflicts.

Usage:
- DO NOT import from `fastcore.security.tokens`.
- ALWAYS import explicitly from the submodules.
  Example: `from fastcore.security.tokens.service import create_token`
           `from fastcore.security.tokens.uuid.service import create_token`
"""

import jwt  # PyJWT

from fastcore.config.settings import get_settings
from fastcore.security.tokens.utils import decode_token

# For patching in tests
__all__ = [
    "get_settings",
    "jwt",
    "decode_token",
]
