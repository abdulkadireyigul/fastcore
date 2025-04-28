"""
Unit tests for simple/grouped security modules.
Covers: security.exceptions, security.models.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from fastcore.security import dependencies
from fastcore.security.exceptions import (
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security.models import Token, TokenType
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
        user_id="uid",
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
        "src.security.dependencies.validate_token",
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
        "src.security.dependencies.validate_token",
        new_callable=AsyncMock,
        side_effect=dependencies.ExpiredTokenError(),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_token_data(token="tok", session=MagicMock(), _=True)
        assert_http_exc(exc, 401, "expired")


@pytest.mark.asyncio
async def test_get_token_data_revoked():
    with patch(
        "src.security.dependencies.validate_token",
        new_callable=AsyncMock,
        side_effect=dependencies.RevokedTokenError(),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.get_token_data(token="tok", session=MagicMock(), _=True)
        assert_http_exc(exc, 401, "revoked")


@pytest.mark.asyncio
async def test_get_token_data_invalid():
    with patch(
        "src.security.dependencies.validate_token",
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
    dep = dependencies.get_current_user_dependency(handler)
    result = await dep({"sub": "user1"})
    assert result == "userobj"
    handler.get_user_by_id.assert_awaited_once_with("user1")


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
        "src.security.dependencies.validate_token",
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
        "src.security.dependencies.validate_token",
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
        "src.security.dependencies.validate_token",
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
        "src.security.dependencies.validate_token",
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
        "src.security.dependencies.refresh_access_token",
        new_callable=AsyncMock,
        return_value="newtoken",
    ):
        result = await dependencies.refresh_token(token="tok", session=MagicMock())
        assert result == "newtoken"


@pytest.mark.asyncio
async def test_refresh_token_error():
    with patch(
        "src.security.dependencies.refresh_access_token",
        new_callable=AsyncMock,
        side_effect=dependencies.InvalidTokenError("fail"),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.refresh_token(token="tok", session=MagicMock())
        assert_http_exc(exc, 401, "fail")


@pytest.mark.asyncio
async def test_logout_user_success():
    with patch(
        "src.security.dependencies.revoke_token", new_callable=AsyncMock
    ) as mock_revoke:
        response = MagicMock()
        result = await dependencies.logout_user(
            token="tok", session=MagicMock(), response=response
        )
        mock_revoke.assert_awaited_once()
        response.delete_cookie.assert_called_once_with(
            key="refresh_token", httponly=True, secure=True, samesite="strict"
        )
        assert result["message"] == "Successfully logged out"


@pytest.mark.asyncio
async def test_logout_user_error():
    with patch(
        "src.security.dependencies.revoke_token",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(HTTPException) as exc:
            await dependencies.logout_user(
                token="tok", session=MagicMock(), response=MagicMock()
            )
        assert_http_exc(exc, 500, "logout failed")
