"""
JWT authentication for FastAPI applications.

This module provides utilities for implementing JWT-based authentication
in FastAPI applications.
"""

import json
from datetime import UTC, datetime, timedelta  # Added UTC import
from typing import Any, Dict, List, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from fastcore.errors.exceptions import AppError, AuthenticationError
from fastcore.logging import get_logger

# Get a logger for this module
logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to check against

    Returns:
        True if the password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


class JWTConfig:
    """Configuration for JWT authentication."""

    # Token settings
    SECRET_KEY: str = "REPLACE_THIS_WITH_A_REAL_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKEN_URL: str = "auth/token"
    TOKEN_TYPE: str = "bearer"

    # Issuer and audience claims
    ISSUER: str = "fastcore-api"
    AUDIENCE: str = "fastcore-client"  # Changed from List to str


# Alias for backwards compatibility
JWTAuthConfig = JWTConfig


class JWTPayload(BaseModel):
    """
    JWT token payload model.

    This class defines the structure of the JWT payload, including standard
    claims and custom claims.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    # Standard JWT claims
    sub: str  # Subject (user ID)
    exp: datetime  # Expiration time
    iat: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )  # Updated to use UTC
    nbf: Optional[datetime] = None  # Not valid before time
    iss: Optional[str] = None  # Issuer
    aud: Optional[str] = None  # Audience - changed from List[str] to str
    jti: Optional[str] = None  # JWT ID (unique identifier for this token)

    # Custom claims for authentication and authorization
    type: str = "access"  # Token type (access or refresh)
    scope: Optional[str] = None  # Space-separated list of scopes
    role: Optional[str] = None  # User role
    permissions: Optional[List[str]] = None  # List of permissions

    # Additional user info (optional)
    username: Optional[str] = None
    email: Optional[str] = None


class TokenResponse(BaseModel):
    """
    Response model for token generation.

    This class defines the structure of the token response returned
    from the token endpoint.
    """

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class JWTAuth:
    """
    JWT authentication handler.

    This class provides methods for creating and validating JWT tokens.

    Example:
        ```python
        # Create a JWT auth handler with default config
        jwt_auth = JWTAuth()

        # Create a token for a user
        token = jwt_auth.create_access_token(
            subject="user123",
            additional_claims={"role": "admin"},
        )

        # Validate a token
        payload = jwt_auth.decode_token(token)
        ```
    """

    def __init__(self, config: JWTConfig = None):
        """
        Initialize a new JWT authentication handler.

        Args:
            config: Optional custom configuration
        """
        self.config = config or JWTConfig()

    def create_access_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None,
        scopes: Optional[List[str]] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new JWT access token.

        Args:
            subject: The subject of the token (usually the user ID)
            expires_delta: Optional custom expiration time
            scopes: Optional list of scopes to include in the token
            additional_claims: Optional additional claims to include in the token

        Returns:
            The encoded JWT token
        """
        # Set the expiration time
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)

        expire = datetime.now(UTC) + expires_delta  # Updated to use UTC

        # Build the token payload
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.now(UTC),  # Updated to use UTC
            "iss": self.config.ISSUER,
            "aud": self.config.AUDIENCE,  # Now a string, not a list
            "type": "access",
        }

        # Add scopes if provided
        if scopes:
            payload["scope"] = " ".join(scopes)

        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)

        # Encode the token
        token = jwt.encode(
            payload,
            self.config.SECRET_KEY,
            algorithm=self.config.ALGORITHM,
        )

        return token

    def create_refresh_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new JWT refresh token.

        Args:
            subject: The subject of the token (usually the user ID)
            expires_delta: Optional custom expiration time
            additional_claims: Optional additional claims to include in the token

        Returns:
            The encoded JWT token
        """
        # Set the expiration time
        if expires_delta is None:
            expires_delta = timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS)

        expire = datetime.now(UTC) + expires_delta  # Updated to use UTC

        # Build the token payload
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.now(UTC),  # Updated to use UTC
            "iss": self.config.ISSUER,
            "aud": self.config.AUDIENCE,
            "type": "refresh",
        }

        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)

        # Encode the token
        token = jwt.encode(
            payload,
            self.config.SECRET_KEY,
            algorithm=self.config.ALGORITHM,
        )

        return token

    def create_token_response(
        self,
        subject: str,
        scopes: Optional[List[str]] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
        include_refresh_token: bool = True,
    ) -> TokenResponse:
        """
        Create a complete token response including access and refresh tokens.

        Args:
            subject: The subject of the token (usually the user ID)
            scopes: Optional list of scopes to include in the token
            additional_claims: Optional additional claims to include in the token
            include_refresh_token: Whether to include a refresh token

        Returns:
            A TokenResponse object with access and optional refresh tokens
        """
        # Create access token
        access_token = self.create_access_token(
            subject=subject,
            scopes=scopes,
            additional_claims=additional_claims,
        )

        # Create refresh token if requested
        refresh_token = None
        if include_refresh_token:
            refresh_token = self.create_refresh_token(
                subject=subject,
                additional_claims=additional_claims,
            )

        # Build the response
        return TokenResponse(
            access_token=access_token,
            token_type=self.config.TOKEN_TYPE,
            expires_in=self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            scope=" ".join(scopes) if scopes else None,
        )

    def decode_token(self, token: str) -> JWTPayload:
        """
        Decode and validate a JWT token.

        This method decodes the token and validates its signature and claims.

        Args:
            token: The JWT token to decode and validate

        Returns:
            The decoded token payload

        Raises:
            AppError: If the token is invalid
        """
        try:
            # Decode the token
            payload = jwt.decode(
                token,
                self.config.SECRET_KEY,
                algorithms=[self.config.ALGORITHM],
                audience=self.config.AUDIENCE,
                issuer=self.config.ISSUER,
            )

            # Convert to JWTPayload model
            return JWTPayload(**payload)

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            # Use AuthenticationError which inherits from AppError and has the correct status_code
            raise AuthenticationError("Token has expired")

        except (JWTError, jwt.JWTClaimsError) as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise AuthenticationError(f"Invalid token: {str(e)}")

        except ValidationError as e:
            logger.warning(f"Invalid token payload: {str(e)}")
            raise AuthenticationError(f"Invalid token payload: {str(e)}")


def create_jwt_auth(
    secret_key: str,
    algorithm: str = "HS256",
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7,
    token_url: str = "auth/token",
    issuer: str = "fastcore-api",
    audience: str = "fastcore-client",  # Changed from List to str
) -> JWTAuth:
    """
    Create a new JWTAuth instance with custom configuration.

    This factory function creates a new JWTAuth instance with the given
    configuration parameters.

    Args:
        secret_key: The secret key to use for signing tokens
        algorithm: The algorithm to use for signing tokens
        access_token_expire_minutes: The expiration time for access tokens in minutes
        refresh_token_expire_days: The expiration time for refresh tokens in days
        token_url: The URL for the token endpoint
        issuer: The issuer claim for tokens
        audience: The audience claim for tokens

    Returns:
        A new JWTAuth instance
    """
    # Create a custom config
    config = JWTConfig()
    config.SECRET_KEY = secret_key
    config.ALGORITHM = algorithm
    config.ACCESS_TOKEN_EXPIRE_MINUTES = access_token_expire_minutes
    config.REFRESH_TOKEN_EXPIRE_DAYS = refresh_token_expire_days
    config.TOKEN_URL = token_url
    config.ISSUER = issuer
    config.AUDIENCE = audience

    # Create and return a new JWTAuth instance
    return JWTAuth(config)


def decode_jwt_token(
    token: str, secret_key: str, algorithm: str = "HS256"
) -> Dict[str, Any]:
    """
    Decode a JWT token.

    This function is provided for compatibility with previous versions.
    New code should use JWTAuth.decode_token() instead.

    Args:
        token: The JWT token to decode
        secret_key: The secret key used to sign the token
        algorithm: The algorithm used to sign the token

    Returns:
        The decoded token payload

    Raises:
        AppError: If the token is invalid
    """
    try:
        # Decode the token with disabled audience validation
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            options={
                "verify_aud": False
            },  # Disable audience validation for compatibility
        )
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise AuthenticationError("Token has expired")

    except JWTError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise AuthenticationError(f"Invalid token: {str(e)}")


def create_access_token(
    subject: str,
    secret_key: str,
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[List[str]] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
    algorithm: str = "HS256",
    expires_minutes: int = 30,
    issuer: str = "fastcore-api",
    audience: str = "fastcore-client",  # Changed from List to str
) -> str:
    """
    Create a new JWT access token.

    This function is provided for compatibility with previous versions.
    New code should use JWTAuth.create_access_token() instead.

    Args:
        subject: The subject of the token (usually the user ID)
        secret_key: The secret key to use for signing the token
        expires_delta: Optional custom expiration time
        scopes: Optional list of scopes to include in the token
        additional_claims: Optional additional claims to include in the token
        algorithm: The algorithm to use for signing the token
        expires_minutes: The default expiration time in minutes (if expires_delta not provided)
        issuer: The issuer claim for the token
        audience: The audience claim for the token

    Returns:
        The encoded JWT token
    """
    # Set the expiration time
    if expires_delta is None:
        expires_delta = timedelta(minutes=expires_minutes)

    expire = datetime.now(UTC) + expires_delta

    # Build the token payload
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "iss": issuer,
        "aud": audience,
        "type": "access",
    }

    # Add scopes if provided
    if scopes:
        payload["scope"] = " ".join(scopes)

    # Add additional claims
    if additional_claims:
        payload.update(additional_claims)

    # Encode the token
    return jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm,
    )
