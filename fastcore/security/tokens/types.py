import enum


class TokenType(str, enum.Enum):
    """
    Enum for token types.

    Features:
    - Supports access and refresh tokens

    Limitations:
    - Only password-based JWT authentication is included by default
    - No advanced RBAC or permission system
    """

    ACCESS = "access"
    REFRESH = "refresh"
