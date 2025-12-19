"""
Unit tests for simple/grouped security modules.
Covers: security.exceptions, security.models.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, Request, Response
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from fastcore.db.base import BaseModel
from fastcore.errors.exceptions import (
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security import dependencies
from fastcore.security.tokens.models import Token, TokenType
from fastcore.security.tokens.uuid.models import UUIDToken
from fastcore.security.users import UserAuthentication


class SecurityTestUser(BaseModel):
    __tablename__ = "security_test_users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    # tokens = relationship("Token",  back_populates="user")
    # tokens = relationship("Token", cascade="all, delete-orphan", back_populates="user")
    legacy_tokens = relationship(
        "Token", back_populates="user", cascade="all, delete-orphan"
    )
    new_uuid_tokens = relationship(
        "UUIDToken", back_populates="user", cascade="all, delete-orphan"
    )
    __table_args__ = {"extend_existing": True}


legacy_user_id_col = Token.__table__.c.user_id
legacy_user_id_col.foreign_keys.clear()
legacy_user_id_col.append_foreign_key(ForeignKey("security_test_users.id"))
Token.user = relationship("SecurityTestUser", back_populates="legacy_tokens")

UUIDToken.__tablename__ = "skipped_uuid_tokens_test"
UUIDToken.__table_args__ = {"extend_existing": True}
UUIDToken.user = relationship("SecurityTestUser", viewonly=True, foreign_keys=[])

# from fastcore.security.models import Token, TokenType
# from fastcore.security.tokens.models import Token, TokenType
from tests.conftest import assert_http_exc

# Use shared dummy_session and dummy_settings fixtures from conftest.py where needed


def test_invalid_token_error():
    err = InvalidTokenError("bad", code="ERR", details={"x": 1})
    assert isinstance(err, Exception)
    assert err.code == "ERR"
    assert err.details == {"x": 1}
    assert "bad" in str(err)


def test_expired_token_error():
    err = ExpiredTokenError("expired", code="EXP", details={"y": 2})
    assert isinstance(err, Exception)
    assert err.code == "EXP"
    assert err.details == {"y": 2}
    assert "expired" in str(err)


def test_revoked_token_error():
    err = RevokedTokenError("revoked", code="REV", details={"z": 3})
    assert isinstance(err, Exception)
    assert err.code == "REV"
    assert err.details == {"z": 3}
    assert "revoked" in str(err)


def test_invalid_credentials_error():
    err = InvalidCredentialsError("fail", code="CRED", details={"a": 4})
    assert isinstance(err, Exception)
    assert err.code == "CRED"
    assert err.details == {"a": 4}
    assert "fail" in str(err)


def test_token_type_enum():
    assert TokenType.ACCESS == "access"
    assert TokenType.REFRESH == "refresh"
    assert TokenType.ACCESS.value == "access"
    assert TokenType.REFRESH.value == "refresh"


def test_token_model_properties():
    now = datetime.now(timezone.utc)
    token = Token(
        token_id="tid",
        user_id=25,
        token_type=TokenType.ACCESS,
        revoked=False,
        expires_at=now + timedelta(hours=1),
        created_at=now,
        updated_at=now,
    )
    assert not token.is_expired
    assert token.is_valid
    token.revoked = True
    assert not token.is_valid
    token.revoked = False
    token.expires_at = now - timedelta(hours=1)
    assert token.is_expired
    assert not token.is_valid
    assert "Token" in repr(token)


@pytest.mark.asyncio
async def test_get_token_data_success():
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        return_value={"sub": "user1"},
    ):
        result = await dependencies.get_token_data(
            token="tok", session=MagicMock(), _=True
        )
        assert result["sub"] == "user1"


@pytest.mark.asyncio
async def test_get_token_data_expired():
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        side_effect=dependencies.ExpiredTokenError(),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_token_data(token="tok", session=MagicMock(), _=True)
        assert_http_exc(exc, 401, "expired")


@pytest.mark.asyncio
async def test_get_token_data_revoked():
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        side_effect=dependencies.RevokedTokenError(),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_token_data(token="tok", session=MagicMock(), _=True)
        assert_http_exc(exc, 401, "revoked")


@pytest.mark.asyncio
async def test_get_token_data_invalid():
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        side_effect=dependencies.InvalidTokenError("fail"),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_token_data(token="tok", session=MagicMock(), _=True)
        assert_http_exc(exc, 401, "fail")


@pytest.mark.asyncio
async def test_get_current_user_dependency_success():
    handler = MagicMock()
    handler.get_user_by_id = AsyncMock(return_value="userobj")
    dep = dependencies.get_current_user_dependency()
    result = await dep({"sub": 26}, handler)
    assert result == "userobj"
    handler.get_user_by_id.assert_awaited_once_with(26)


@pytest.mark.asyncio
async def test_get_current_user_dependency_no_sub():
    handler = MagicMock()
    dep = dependencies.get_current_user_dependency(handler)
    with pytest.raises(HTTPException) as exc:
        await dep({})
    assert_http_exc(exc, 401, "invalid token content")


@pytest.mark.asyncio
async def test_get_current_user_dependency_user_not_found():
    handler = MagicMock()
    handler.get_user_by_id = AsyncMock(return_value=None)
    dep = dependencies.get_current_user_dependency(handler)
    with pytest.raises(HTTPException) as exc:
        await dep({"sub": "user1"})
    assert_http_exc(exc, 401, "could not validate user")


@pytest.mark.asyncio
async def test_get_current_user_dependency_exception():
    handler = MagicMock()
    handler.get_user_by_id = AsyncMock(side_effect=Exception("fail"))
    dep = dependencies.get_current_user_dependency(handler)
    with pytest.raises(HTTPException) as exc:
        await dep({"sub": "user1"})
    assert_http_exc(exc, 401, "could not validate user")


@pytest.mark.asyncio
async def test_get_refresh_token_data_success():
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        return_value={"sub": "user1"},
    ):
        result = await dependencies.get_refresh_token_data(
            token="tok", session=MagicMock(), _=True
        )
        assert result["sub"] == "user1"


@pytest.mark.asyncio
async def test_get_refresh_token_data_expired():
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        side_effect=dependencies.ExpiredTokenError(),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_refresh_token_data(
                token="tok", session=MagicMock(), _=True
            )
        assert_http_exc(exc, 401, "expired")


@pytest.mark.asyncio
async def test_get_refresh_token_data_revoked():
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        side_effect=dependencies.RevokedTokenError(),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_refresh_token_data(
                token="tok", session=MagicMock(), _=True
            )
        assert_http_exc(exc, 401, "revoked")


@pytest.mark.asyncio
async def test_get_refresh_token_data_invalid():
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        side_effect=dependencies.InvalidTokenError("fail"),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_refresh_token_data(
                token="tok", session=MagicMock(), _=True
            )
        assert_http_exc(exc, 401, "fail")


@pytest.mark.asyncio
async def test_refresh_token_success():
    with patch(
        "fastcore.security.tokens.service.refresh_access_token",
        new_callable=AsyncMock,
        return_value="newtoken",
    ):
        result = await dependencies.refresh_token(token="tok", session=MagicMock())
        assert result == "newtoken"


@pytest.mark.asyncio
async def test_refresh_token_error():
    with patch(
        "fastcore.security.tokens.service.refresh_access_token",
        new_callable=AsyncMock,
        side_effect=dependencies.InvalidTokenError("fail"),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.refresh_token(token="tok", session=MagicMock())
        assert_http_exc(exc, 401, "fail")


# @pytest.mark.asyncio
# async def test_logout_user_success():
#     with patch(
#         "fastcore.security.tokens.service.revoke_token", new_callable=AsyncMock
#     ) as mock_revoke:
#         response = MagicMock()
#         result = await dependencies.logout_user(
#             token="tok", session=MagicMock(), response=response
#         )
#         mock_revoke.assert_awaited_once()
#         response.delete_cookie.assert_called_once_with(
#             key="refresh_token", httponly=True, secure=True, samesite="strict"
#         )
#         assert result["message"] == "Successfully logged out"


@pytest.mark.asyncio
async def test_logout_user_error():
    with patch(
        "fastcore.security.tokens.service.revoke_token",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.logout_user(
                token="tok", session=MagicMock(), response=MagicMock()
            )
        assert_http_exc(exc, 500, "logout failed")


# -----------------------------
# Cookie-based authentication tests
# -----------------------------

from sqlalchemy.ext.asyncio import AsyncSession

# Import the functions to test
from fastcore.security.dependencies import (
    get_current_user_from_cookie_dependency,
    get_token_data_from_cookie,
    logout_user_cookie,
    remove_auth_cookies,
    set_auth_cookies,
)


# Fixtures
@pytest.fixture
def mock_request():
    """Create a mock request with cookies."""
    request = Mock(spec=Request)
    request.cookies = {"access_token": "valid_token_123"}
    return request


@pytest.fixture
def mock_request_no_token():
    """Create a mock request without cookies."""
    request = Mock(spec=Request)
    request.cookies = {}
    return request


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return Mock(spec=AsyncSession)


@pytest.fixture
def mock_response():
    """Create a mock FastAPI response."""
    response = Mock(spec=Response)
    response.set_cookie = Mock()
    response.delete_cookie = Mock()
    return response


@pytest.fixture
def mock_auth_handler():
    """Create a mock authentication handler."""
    auth_handler = Mock(spec=UserAuthentication)
    auth_handler.get_user_by_id = AsyncMock()
    return auth_handler


@pytest.fixture
def mock_security_status():
    """Mock security status check."""
    return True


# Tests for get_token_data_from_cookie
@pytest.mark.asyncio
async def test_get_token_data_from_cookie_valid_token(
    mock_request, mock_session, mock_security_status
):
    """Test successful token validation from cookie."""
    expected_token_data = {"sub": "123", "exp": 1234567890}

    with patch(
        "fastcore.security.base_dependencies.BaseSecurityDependencies.get_token_data"
    ) as mock_get_token_data:
        mock_get_token_data.return_value = expected_token_data

        result = await get_token_data_from_cookie(
            request=mock_request,
            session=mock_session,
            _=mock_security_status,
            token_type=TokenType.ACCESS,
        )

        assert result == expected_token_data
        mock_get_token_data.assert_called_once_with(
            "valid_token_123", mock_session, mock_security_status, TokenType.ACCESS
        )


@pytest.mark.asyncio
async def test_get_token_data_from_cookie_no_token(mock_session, mock_security_status):
    """Test when no access token is found in cookies."""
    request = Mock(spec=Request)
    request.cookies = {}  # Empty cookies

    with pytest.raises(HTTPException) as exc_info:
        await get_token_data_from_cookie(
            request=request, session=mock_session, _=mock_security_status
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "No authentication token found"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_get_token_data_from_cookie_empty_token(
    mock_session, mock_security_status
):
    """Test when access token is empty in cookies."""
    request = Mock(spec=Request)
    request.cookies = {"access_token": ""}

    with pytest.raises(HTTPException) as exc_info:
        await get_token_data_from_cookie(
            request=request, session=mock_session, _=mock_security_status
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "No authentication token found"


@pytest.mark.asyncio
async def test_get_token_data_from_cookie_none_token(
    mock_session, mock_security_status
):
    """Test when access token is None in cookies."""
    request = Mock(spec=Request)
    request.cookies = {"access_token": None}

    with pytest.raises(HTTPException) as exc_info:
        await get_token_data_from_cookie(
            request=request, session=mock_session, _=mock_security_status
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "No authentication token found"


@pytest.mark.asyncio
async def test_get_token_data_from_cookie_refresh_token_type(
    mock_request, mock_session, mock_security_status
):
    """Test with refresh token type."""
    expected_token_data = {"sub": "123", "type": "refresh"}

    with patch(
        "fastcore.security.base_dependencies.BaseSecurityDependencies.get_token_data"
    ) as mock_get_token_data:
        mock_get_token_data.return_value = expected_token_data

        result = await get_token_data_from_cookie(
            request=mock_request,
            session=mock_session,
            _=mock_security_status,
            token_type=TokenType.REFRESH,
        )

        assert result == expected_token_data
        mock_get_token_data.assert_called_once_with(
            "valid_token_123", mock_session, mock_security_status, TokenType.REFRESH
        )


@pytest.mark.asyncio
async def test_get_token_data_from_cookie_exception_propagation(
    mock_request, mock_session, mock_security_status
):
    """Test that token validation exceptions are properly propagated."""
    with patch(
        "fastcore.security.base_dependencies.BaseSecurityDependencies.get_token_data"
    ) as mock_get_token_data:
        mock_get_token_data.side_effect = HTTPException(
            status_code=401, detail="Token expired"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_token_data_from_cookie(
                request=mock_request, session=mock_session, _=mock_security_status
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token expired"


# Tests for get_current_user_from_cookie_dependency
@pytest.mark.asyncio
async def test_get_current_user_from_cookie_dependency_success(mock_auth_handler):
    """Test successful user retrieval from cookie token."""
    token_data = {"sub": "123", "exp": 1234567890}
    test_user = SecurityTestUser(id=123, username="testuser")
    mock_auth_handler.get_user_by_id.return_value = test_user

    mock_auth_handler_dependency = Mock(return_value=mock_auth_handler)
    current_user_dependency = get_current_user_from_cookie_dependency(
        mock_auth_handler_dependency
    )

    result = await current_user_dependency(token_data, mock_auth_handler)

    assert result == test_user
    mock_auth_handler.get_user_by_id.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_get_current_user_from_cookie_dependency_missing_user_id(
    mock_auth_handler,
):
    """Test when token data doesn't contain user ID."""
    token_data = {"exp": 1234567890}  # Missing 'sub' field

    mock_auth_handler_dependency = Mock(return_value=mock_auth_handler)
    current_user_dependency = get_current_user_from_cookie_dependency(
        mock_auth_handler_dependency
    )

    with pytest.raises(HTTPException) as exc_info:
        await current_user_dependency(token_data, mock_auth_handler)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token content"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_get_current_user_from_cookie_dependency_empty_user_id(mock_auth_handler):
    """Test when token contains empty user ID."""
    token_data = {"sub": "", "exp": 1234567890}

    mock_auth_handler_dependency = Mock(return_value=mock_auth_handler)
    current_user_dependency = get_current_user_from_cookie_dependency(
        mock_auth_handler_dependency
    )

    with pytest.raises(HTTPException) as exc_info:
        await current_user_dependency(token_data, mock_auth_handler)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token content"


@pytest.mark.asyncio
async def test_get_current_user_from_cookie_dependency_user_not_found(
    mock_auth_handler,
):
    """Test when user is not found in database."""
    token_data = {"sub": "999", "exp": 1234567890}
    mock_auth_handler.get_user_by_id.return_value = None

    mock_auth_handler_dependency = Mock(return_value=mock_auth_handler)
    current_user_dependency = get_current_user_from_cookie_dependency(
        mock_auth_handler_dependency
    )

    with pytest.raises(HTTPException) as exc_info:
        await current_user_dependency(token_data, mock_auth_handler)

    assert exc_info.value.status_code == 401
    # The actual implementation catches the None user and wraps it in a generic exception
    assert "Could not validate user:" in exc_info.value.detail
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_get_current_user_from_cookie_dependency_database_exception(
    mock_auth_handler,
):
    """Test when database operation raises an exception."""
    token_data = {"sub": "123", "exp": 1234567890}
    mock_auth_handler.get_user_by_id.side_effect = Exception(
        "Database connection error"
    )

    mock_auth_handler_dependency = Mock(return_value=mock_auth_handler)
    current_user_dependency = get_current_user_from_cookie_dependency(
        mock_auth_handler_dependency
    )

    with pytest.raises(HTTPException) as exc_info:
        await current_user_dependency(token_data, mock_auth_handler)

    assert exc_info.value.status_code == 401
    assert "Could not validate user: Database connection error" in exc_info.value.detail
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_get_current_user_from_cookie_dependency_invalid_user_id_format(
    mock_auth_handler,
):
    """Test when user ID cannot be converted to integer."""
    token_data = {"sub": "not_a_number", "exp": 1234567890}

    mock_auth_handler_dependency = Mock(return_value=mock_auth_handler)
    current_user_dependency = get_current_user_from_cookie_dependency(
        mock_auth_handler_dependency
    )

    with pytest.raises(HTTPException) as exc_info:
        await current_user_dependency(token_data, mock_auth_handler)

    assert exc_info.value.status_code == 401
    assert "Could not validate user:" in exc_info.value.detail


# Tests for set_auth_cookies
def test_set_auth_cookies_access_token_only(mock_response):
    """Test setting only access token cookie."""
    with patch.dict(
        os.environ, {"APP_ENV": "production", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "60"}
    ):
        set_auth_cookies(response=mock_response, access_token="access_token_123")

        mock_response.set_cookie.assert_called_once_with(
            key="access_token",
            value="access_token_123",
            max_age=3600,  # 60 minutes * 60 seconds
            httponly=True,
            secure=True,  # Production environment
            samesite="none",
        )


def test_set_auth_cookies_both_tokens(mock_response):
    """Test setting both access and refresh token cookies."""
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "7",
        },
    ):
        set_auth_cookies(
            response=mock_response,
            access_token="access_token_123",
            refresh_token="refresh_token_456",
        )

        assert mock_response.set_cookie.call_count == 2

        # Check access token call
        access_call = mock_response.set_cookie.call_args_list[0]
        assert access_call.kwargs["key"] == "access_token"
        assert access_call.kwargs["value"] == "access_token_123"
        assert access_call.kwargs["max_age"] == 1800  # 30 minutes * 60 seconds
        assert access_call.kwargs["secure"] is True

        # Check refresh token call
        refresh_call = mock_response.set_cookie.call_args_list[1]
        assert refresh_call.kwargs["key"] == "refresh_token"
        assert refresh_call.kwargs["value"] == "refresh_token_456"
        assert refresh_call.kwargs["max_age"] == 604800  # 7 days * 86400 seconds
        assert refresh_call.kwargs["secure"] is True


def test_set_auth_cookies_development_environment(mock_response):
    """Test that secure flag is False in development environment."""
    with patch.dict(os.environ, {"APP_ENV": "development"}):
        set_auth_cookies(response=mock_response, access_token="access_token_123")

        call_kwargs = mock_response.set_cookie.call_args.kwargs
        assert call_kwargs["secure"] is False


def test_set_auth_cookies_default_expiration_times(mock_response):
    """Test default expiration times when env vars are not set."""
    # Clear environment variables
    with patch.dict(os.environ, {}, clear=True):
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            set_auth_cookies(
                response=mock_response,
                access_token="access_token_123",
                refresh_token="refresh_token_456",
            )

            access_call = mock_response.set_cookie.call_args_list[0]
            refresh_call = mock_response.set_cookie.call_args_list[1]

            assert access_call.kwargs["max_age"] == 1800  # Default 30 minutes
            assert refresh_call.kwargs["max_age"] == 604800  # Default 7 days


def test_set_auth_cookies_custom_expiration_times(mock_response):
    """Test custom expiration times from environment variables."""
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "120",  # 2 hours
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "14",  # 2 weeks
        },
    ):
        set_auth_cookies(
            response=mock_response,
            access_token="access_token_123",
            refresh_token="refresh_token_456",
        )

        access_call = mock_response.set_cookie.call_args_list[0]
        refresh_call = mock_response.set_cookie.call_args_list[1]

        assert access_call.kwargs["max_age"] == 7200  # 120 minutes * 60 seconds
        assert refresh_call.kwargs["max_age"] == 1209600  # 14 days * 86400 seconds


def test_set_auth_cookies_only_refresh_token(mock_response):
    """Test setting only refresh token (access token is None)."""
    with patch.dict(os.environ, {"APP_ENV": "production"}):
        set_auth_cookies(
            response=mock_response, access_token=None, refresh_token="refresh_token_456"
        )

        mock_response.set_cookie.assert_called_once_with(
            key="refresh_token",
            value="refresh_token_456",
            max_age=604800,  # Default 7 days
            httponly=True,
            secure=True,
            samesite="none",
        )


def test_set_auth_cookies_cookie_attributes(mock_response):
    """Test that all cookie attributes are set correctly."""
    with patch.dict(os.environ, {"APP_ENV": "production"}):
        set_auth_cookies(response=mock_response, access_token="access_token_123")

        call_kwargs = mock_response.set_cookie.call_args.kwargs
        assert call_kwargs["httponly"] is True
        assert call_kwargs["secure"] is True
        assert call_kwargs["samesite"] == "none"


# Tests for logout_user_cookie
@pytest.mark.asyncio
async def test_logout_user_cookie_success(mock_request, mock_session, mock_response):
    """Test successful logout with token revocation and cookie clearing."""
    expected_result = {"message": "Successfully logged out"}

    with patch(
        "fastcore.security.base_dependencies.BaseSecurityDependencies.logout_user"
    ) as mock_logout_user:
        mock_logout_user.return_value = expected_result

        result = await logout_user_cookie(
            request=mock_request, session=mock_session, response=mock_response
        )

        assert result == expected_result
        mock_logout_user.assert_called_once_with(
            "valid_token_123", mock_session, mock_response
        )


@pytest.mark.asyncio
async def test_logout_user_cookie_no_token(
    mock_request_no_token, mock_session, mock_response
):
    """Test logout when no access token is found in cookies."""
    with pytest.raises(HTTPException) as exc_info:
        await logout_user_cookie(
            request=mock_request_no_token, session=mock_session, response=mock_response
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "No authentication token found"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_logout_user_cookie_empty_token(mock_session, mock_response):
    """Test logout when access token is empty in cookies."""
    request = Mock(spec=Request)
    request.cookies = {"access_token": ""}

    with pytest.raises(HTTPException) as exc_info:
        await logout_user_cookie(
            request=request, session=mock_session, response=mock_response
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "No authentication token found"


@pytest.mark.asyncio
async def test_logout_user_cookie_none_token(mock_session, mock_response):
    """Test logout when access token is None in cookies."""
    request = Mock(spec=Request)
    request.cookies = {"access_token": None}

    with pytest.raises(HTTPException) as exc_info:
        await logout_user_cookie(
            request=request, session=mock_session, response=mock_response
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "No authentication token found"


@pytest.mark.asyncio
async def test_logout_user_cookie_without_response(mock_request, mock_session):
    """Test logout without providing response object."""
    expected_result = {"message": "Successfully logged out"}

    with patch(
        "fastcore.security.base_dependencies.BaseSecurityDependencies.logout_user"
    ) as mock_logout_user:
        mock_logout_user.return_value = expected_result

        result = await logout_user_cookie(
            request=mock_request, session=mock_session, response=None
        )

        assert result == expected_result
        mock_logout_user.assert_called_once_with("valid_token_123", mock_session, None)


@pytest.mark.asyncio
async def test_logout_user_cookie_exception_propagation(
    mock_request, mock_session, mock_response
):
    """Test that exceptions from logout_user are properly propagated."""
    with patch(
        "fastcore.security.base_dependencies.BaseSecurityDependencies.logout_user"
    ) as mock_logout_user:
        mock_logout_user.side_effect = HTTPException(
            status_code=401, detail="Token already revoked"
        )

        with pytest.raises(HTTPException) as exc_info:
            await logout_user_cookie(
                request=mock_request, session=mock_session, response=mock_response
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token already revoked"


# Integration tests
@pytest.mark.asyncio
async def test_full_cookie_auth_flow():
    """Test complete cookie authentication flow from setting to validation."""
    # Setup mocks
    mock_response = Mock(spec=Response)
    mock_response.set_cookie = Mock()
    mock_request = Mock(spec=Request)
    mock_session = Mock(spec=AsyncSession)
    mock_auth_handler = Mock(spec=UserAuthentication)
    mock_auth_handler.get_user_by_id = AsyncMock()

    # Step 1: Set authentication cookies
    access_token = "test_access_token"
    refresh_token = "test_refresh_token"

    with patch.dict(os.environ, {"APP_ENV": "development"}):
        set_auth_cookies(mock_response, access_token, refresh_token)

    # Verify cookies were set
    assert mock_response.set_cookie.call_count == 2

    # Step 2: Simulate request with cookies
    mock_request.cookies = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

    # Step 3: Validate token from cookie
    expected_token_data = {"sub": "123", "exp": 1234567890}
    test_user = SecurityTestUser(id=123, username="testuser")
    mock_auth_handler.get_user_by_id.return_value = test_user

    with patch(
        "fastcore.security.base_dependencies.BaseSecurityDependencies.get_token_data"
    ) as mock_get_token_data:
        mock_get_token_data.return_value = expected_token_data

        # Get token data from cookie
        token_data = await get_token_data_from_cookie(
            request=mock_request, session=mock_session, _=True
        )

        assert token_data == expected_token_data

        # Get user from token data
        current_user_dependency = get_current_user_from_cookie_dependency(
            lambda: mock_auth_handler
        )
        user = await current_user_dependency(token_data, mock_auth_handler)

        assert user == test_user
        assert user.id == 123
        assert user.username == "testuser"


@pytest.mark.asyncio
async def test_cookie_logout_flow():
    """Test complete cookie logout flow."""
    mock_request = Mock(spec=Request)
    mock_request.cookies = {"access_token": "valid_token"}
    mock_session = Mock(spec=AsyncSession)
    mock_response = Mock(spec=Response)

    expected_result = {"message": "Successfully logged out"}

    with patch(
        "fastcore.security.base_dependencies.BaseSecurityDependencies.logout_user"
    ) as mock_logout_user:
        mock_logout_user.return_value = expected_result

        result = await logout_user_cookie(mock_request, mock_session, mock_response)

        assert result == expected_result
        mock_logout_user.assert_called_once_with(
            "valid_token", mock_session, mock_response
        )


@pytest.mark.asyncio
async def test_remove_auth_cookies_dev_env(monkeypatch):
    # Arrange
    monkeypatch.setenv("APP_ENV", "development")
    response = MagicMock(spec=Response)

    # Act
    result = await remove_auth_cookies(response)

    # Assert
    assert result == {"message": "Successfully removed the auth cookies"}
    response.delete_cookie.assert_any_call(
        key="access_token",
        httponly=True,
        secure=False,  # dev env -> secure = False
        samesite="strict",
    )
    response.delete_cookie.assert_any_call(
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="strict",
    )


@pytest.mark.asyncio
async def test_remove_auth_cookies_prod_env(monkeypatch):
    # Arrange
    monkeypatch.setenv("APP_ENV", "production")
    response = MagicMock(spec=Response)

    # Act
    result = await remove_auth_cookies(response)

    # Assert
    assert result == {"message": "Successfully removed the auth cookies"}
    response.delete_cookie.assert_any_call(
        key="access_token",
        httponly=True,
        secure=True,  # prod env -> secure = True
        samesite="none",
    )
    response.delete_cookie.assert_any_call(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="none",
    )


@pytest.mark.asyncio
async def test_remove_auth_cookies_no_response(monkeypatch):
    # Arrange
    monkeypatch.setenv("APP_ENV", "production")

    # Act
    result = await remove_auth_cookies(None)

    # Assert
    assert result == {"message": "Successfully removed the auth cookies"}
    # no response object -> no delete_cookie call
