"""
Tests for JWT authentication in the security module.
"""

import time
from datetime import UTC, datetime, timedelta  # Added UTC import
from typing import Any, Dict

import pytest
from jose import jwt
from pydantic import ValidationError

from fastcore.errors.exceptions import AuthenticationError
from fastcore.security.auth import (
    JWTAuth,
    JWTConfig,
    JWTPayload,
    TokenResponse,
    create_access_token,
    decode_jwt_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test that a password can be hashed and verified."""
        password = "test-password-123"
        hashed = get_password_hash(password)

        # Hashed should not be plaintext
        assert hashed != password

        # Should verify correctly
        assert verify_password(password, hashed)

        # Incorrect password should not verify
        assert not verify_password("wrong-password", hashed)


class TestJWTAuth:
    """Test JWT authentication."""

    @pytest.fixture
    def jwt_config(self):
        """Create a JWT config for testing."""
        config = JWTConfig()
        config.SECRET_KEY = "test-secret-key"
        config.ALGORITHM = "HS256"
        config.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        config.ISSUER = "test-issuer"
        config.AUDIENCE = "test-audience"  # Changed from list to string
        return config

    @pytest.fixture
    def jwt_auth(self, jwt_config):
        """Create a JWT auth instance for testing."""
        return JWTAuth(jwt_config)

    def test_create_access_token(self, jwt_auth):
        """Test creating an access token."""
        token = jwt_auth.create_access_token(
            subject="test-user",
            scopes=["users:read", "items:write"],
            additional_claims={"role": "admin"},
        )

        # Token should be a string
        assert isinstance(token, str)

        # Decode the token manually to verify
        payload = jwt.decode(
            token,
            jwt_auth.config.SECRET_KEY,
            algorithms=[jwt_auth.config.ALGORITHM],
            audience=jwt_auth.config.AUDIENCE,
        )

        # Check subject
        assert payload["sub"] == "test-user"

        # Check scopes
        assert payload["scope"] == "users:read items:write"

        # Check additional claims
        assert payload["role"] == "admin"

        # Check standard claims
        assert "iat" in payload
        assert "exp" in payload
        assert payload["iss"] == jwt_auth.config.ISSUER

    def test_create_refresh_token(self, jwt_auth):
        """Test creating a refresh token."""
        token = jwt_auth.create_refresh_token(
            subject="test-user", additional_claims={"role": "admin"}
        )

        # Token should be a string
        assert isinstance(token, str)

        # Decode the token manually to verify
        payload = jwt.decode(
            token,
            jwt_auth.config.SECRET_KEY,
            algorithms=[jwt_auth.config.ALGORITHM],
            audience=jwt_auth.config.AUDIENCE,
        )

        # Check token type
        assert payload["type"] == "refresh"

        # Check subject
        assert payload["sub"] == "test-user"

        # Check additional claims
        assert payload["role"] == "admin"

        # Check expiration time
        expiration = datetime.fromtimestamp(payload["exp"])
        issue_time = datetime.fromtimestamp(payload["iat"])
        days_diff = (expiration - issue_time).days
        assert days_diff >= jwt_auth.config.REFRESH_TOKEN_EXPIRE_DAYS - 1

    def test_create_token_response(self, jwt_auth):
        """Test creating a token response."""
        response = jwt_auth.create_token_response(
            subject="test-user",
            scopes=["users:read", "items:write"],
            additional_claims={"role": "admin"},
            include_refresh_token=True,
        )

        # Check response
        assert response.access_token
        assert response.refresh_token
        assert response.token_type == jwt_auth.config.TOKEN_TYPE
        assert response.scope == "users:read items:write"
        assert response.expires_in == jwt_auth.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_decode_token(self, jwt_auth):
        """Test decoding a JWT token."""
        # Create a token
        token = jwt_auth.create_access_token(
            subject="test-user",
            scopes=["users:read"],
            additional_claims={"role": "admin"},
        )

        # Decode the token
        payload = jwt_auth.decode_token(token)

        # Check payload
        assert isinstance(payload, JWTPayload)
        assert payload.sub == "test-user"
        assert payload.scope == "users:read"
        assert payload.role == "admin"
        assert payload.type == "access"

    def test_expired_token(self, jwt_auth):
        """Test that expired tokens are rejected."""
        # Create a token that expires immediately
        token = jwt_auth.create_access_token(
            subject="test-user", expires_delta=timedelta(seconds=-1)  # Already expired
        )

        # Should raise an error when decoding
        with pytest.raises(
            AuthenticationError
        ) as excinfo:  # Changed from AppError to AuthenticationError
            jwt_auth.decode_token(token)

        assert "expired" in str(excinfo.value).lower()

    def test_invalid_token(self, jwt_auth):
        """Test that invalid tokens are rejected."""
        # Invalid token
        token = "invalid.token.string"

        # Should raise an error when decoding
        with pytest.raises(
            AuthenticationError
        ) as excinfo:  # Changed from AppError to AuthenticationError
            jwt_auth.decode_token(token)

        assert "invalid" in str(excinfo.value).lower()


class TestCompatibilityFunctions:
    """Test compatibility functions for older code."""

    def test_create_access_token_compatibility(self):
        """Test the compatibility function for creating tokens."""
        secret_key = "test-secret-key"
        token = create_access_token(
            subject="test-user",
            secret_key=secret_key,
            scopes=["test:scope"],
            additional_claims={"role": "user"},
        )

        # Token should be a string
        assert isinstance(token, str)

        # Decode the token manually to verify
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            audience="fastcore-client",  # Specify the audience to match what's in the token
        )

        # Check subject
        assert payload["sub"] == "test-user"

        # Check scopes
        assert payload["scope"] == "test:scope"

        # Check additional claims
        assert payload["role"] == "user"

    def test_decode_jwt_token_compatibility(self):
        """Test the compatibility function for decoding tokens."""
        secret_key = "test-secret-key"
        token = create_access_token(subject="test-user", secret_key=secret_key)

        # Decode the token using compatibility function
        payload = decode_jwt_token(token, secret_key)

        # Check payload
        assert payload["sub"] == "test-user"
        assert payload["type"] == "access"

    def test_decode_jwt_token_error(self):
        """Test error handling in the compatibility function."""
        with pytest.raises(
            AuthenticationError
        ) as excinfo:  # Changed from AppError to AuthenticationError
            decode_jwt_token("invalid.token", "secret")

        assert "invalid" in str(excinfo.value).lower()
