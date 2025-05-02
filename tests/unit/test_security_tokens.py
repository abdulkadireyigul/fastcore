"""
Unit tests for the fastcore.security.tokens module.
Covers: token creation, validation, revocation, and error handling.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from fastcore.errors.exceptions import DBError
from fastcore.security.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    RevokedTokenError,
)
from fastcore.security.tokens.models import Token, TokenType
from fastcore.security.tokens.repository import TokenRepository
from fastcore.security.tokens.service import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    refresh_access_token,
    revoke_all_tokens_for_user,
    revoke_token,
    validate_token,
)
from fastcore.security.tokens.utils import decode_token


# --- Helpers ---
def make_mock_scalars(first=None, all_=None):
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = first
    mock_scalars.all.return_value = all_ or []
    return mock_scalars


def make_mock_result(first=None, all_=None, rowcount=None):
    mock_result = MagicMock()
    mock_result.scalars.return_value = make_mock_scalars(first, all_)
    if rowcount is not None:
        mock_result.rowcount = rowcount
    return mock_result


# --- TokenRepository tests ---
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method, args, exc_msg",
    [
        ("get_by_token_id", ("abc",), "fail-get-by-token-id"),
        ("get_by_user_id", (1,), "fail-get-by-user-id"),
        ("get_refresh_token_for_user", (1,), "fail-refresh-token"),
        ("revoke_token_for_user", (1, "abc"), "fail-revoke-token"),
        ("revoke_all_for_user", (1,), "fail-revoke-all"),
    ],
)
async def test_token_repository_db_error_branches(dummy_session, method, args, exc_msg):
    repo = TokenRepository(Token, dummy_session)
    dummy_session.execute = AsyncMock(side_effect=Exception(exc_msg))
    with patch("sqlalchemy.update") if method == "revoke_all_for_user" else patch(
        "builtins.id"
    ):
        with pytest.raises(DBError) as exc:
            await getattr(repo, method)(*args)
        assert exc_msg in str(exc.value)


@pytest.mark.asyncio
async def test_token_repository_get_by_token_id_success_short(dummy_session):
    repo = TokenRepository(Token, dummy_session)
    dummy_token = MagicMock(token_id="abc")
    dummy_session.execute = AsyncMock(return_value=make_mock_result(first=dummy_token))
    token = await repo.get_by_token_id("abc")
    assert token.token_id == "abc"


@pytest.mark.asyncio
async def test_token_repository_get_by_user_id_success(dummy_session):
    repo = TokenRepository(Token, dummy_session)
    dummy_tokens = [MagicMock(token_id="a"), MagicMock(token_id="b")]
    dummy_session.execute = AsyncMock(return_value=make_mock_result(all_=dummy_tokens))
    tokens = await repo.get_by_user_id(1)
    assert tokens == dummy_tokens


@pytest.mark.asyncio
async def test_token_repository_revoke_token_for_user_logger_warning(dummy_session):
    repo = TokenRepository(Token, dummy_session)
    dummy_session.execute = AsyncMock(return_value=make_mock_result(first=None))
    await repo.revoke_token_for_user(1, "notfound-logger")


@pytest.mark.asyncio
async def test_token_repository_revoke_all_for_user_rows_affected(dummy_session):
    repo = TokenRepository(Token, dummy_session)
    dummy_session.execute = AsyncMock(return_value=make_mock_result(rowcount=3))
    dummy_session.flush = AsyncMock()
    with patch("sqlalchemy.update"):
        await repo.revoke_all_for_user(1)
    dummy_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_token_repository_revoke_all_for_user_no_rowcount(dummy_session):
    repo = TokenRepository(Token, dummy_session)
    mock_result = make_mock_result()
    if hasattr(mock_result, "rowcount"):
        delattr(mock_result, "rowcount")
    dummy_session.execute = AsyncMock(return_value=mock_result)
    dummy_session.flush = AsyncMock()
    with patch("sqlalchemy.update"):
        await repo.revoke_all_for_user(1)
    dummy_session.flush.assert_awaited()


# --- Token creation tests (DRY) ---
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service_func, token_type, jwt_value",
    [
        (create_access_token, "access", "jwt_token"),
        (create_refresh_token, "refresh", "jwt_refresh"),
    ],
)
async def test_create_token_success_and_db_error(
    dummy_settings, dummy_session, service_func, token_type, jwt_value
):
    dummy_session.commit = AsyncMock()
    dummy_session.rollback = AsyncMock()
    # Success
    with patch("fastcore.security.tokens.jwt.encode", return_value=jwt_value), patch(
        "fastcore.security.tokens.TokenRepository.create", new_callable=AsyncMock
    ):
        token = await service_func({"sub": 26}, dummy_session)
        assert token == jwt_value
    # DBError
    with patch("fastcore.security.tokens.jwt.encode", return_value=jwt_value), patch(
        "fastcore.security.tokens.TokenRepository.create",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError) as exc:
            await service_func({"sub": 26}, dummy_session)
        assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_create_token_pair_success(dummy_settings, dummy_session):
    # Patch the actual service function, not just the helpers
    with patch(
        "fastcore.security.tokens.service.create_access_token",
        new_callable=AsyncMock,
        return_value="access",
    ), patch(
        "fastcore.security.tokens.service.create_refresh_token",
        new_callable=AsyncMock,
        return_value="refresh",
    ):
        pair = await create_token_pair({"sub": 26}, dummy_session)
        assert pair["access_token"] == "access"
        assert pair["refresh_token"] == "refresh"
        assert pair["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_create_token_error_branch(dummy_session):
    from fastcore.security.tokens.service import create_token

    with patch(
        "fastcore.security.tokens.repository.TokenRepository.create",
        new_callable=AsyncMock,
        side_effect=Exception("fail-create-token"),
    ):
        with pytest.raises(DBError) as exc:
            await create_token({"sub": 1}, dummy_session)
        assert "fail-create-token" in str(exc.value)


@pytest.mark.asyncio
async def test_create_token_success_logger(dummy_session):
    from fastcore.security.tokens.service import create_token

    with patch(
        "fastcore.security.tokens.repository.TokenRepository.create",
        new_callable=AsyncMock,
    ):
        token = await create_token({"sub": 1}, dummy_session)
        assert isinstance(token, str)


@pytest.mark.asyncio
async def test_create_token_logger_info(dummy_session):
    from fastcore.security.tokens.service import create_token

    # Patch TokenRepository.create to succeed
    with patch(
        "fastcore.security.tokens.repository.TokenRepository.create",
        new_callable=AsyncMock,
    ):
        token = await create_token({"sub": 1}, dummy_session)
        assert isinstance(token, str)


# --- Service and Utils tests (refactored) ---
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service_func,patches,raises,assertion",
    [
        (
            create_access_token,
            [
                "fastcore.security.tokens.jwt.encode",
                "fastcore.security.tokens.TokenRepository.create",
            ],
            None,
            lambda token: token == "jwt_token",
        ),
        (
            create_refresh_token,
            [
                "fastcore.security.tokens.jwt.encode",
                "fastcore.security.tokens.TokenRepository.create",
            ],
            None,
            lambda token: token == "jwt_refresh",
        ),
        (
            create_access_token,
            [
                "fastcore.security.tokens.jwt.encode",
                "fastcore.security.tokens.TokenRepository.create",
            ],
            DBError,
            None,
        ),
        (
            create_refresh_token,
            [
                "fastcore.security.tokens.jwt.encode",
                "fastcore.security.tokens.TokenRepository.create",
            ],
            DBError,
            None,
        ),
    ],
)
async def test_token_creation_variants(
    dummy_settings, dummy_session, service_func, patches, raises, assertion
):
    # Ensure dummy_session has async commit/rollback
    dummy_session.commit = AsyncMock()
    dummy_session.rollback = AsyncMock()
    patchers = [
        patch(
            p,
            return_value="jwt_token"
            if "access" in service_func.__name__
            else "jwt_refresh",
        )
        if "encode" in p
        else patch(
            p, new_callable=AsyncMock, side_effect=Exception("fail") if raises else None
        )
        for p in patches
    ]
    with patchers[0] as p1, patchers[1] as p2:
        if raises:
            with pytest.raises(DBError):
                await service_func({"sub": 26}, dummy_session)
        else:
            result = await service_func({"sub": 26}, dummy_session)
            assert assertion(result)


# --- Token decode/validate tests (DRY) ---
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "decode_side_effect,raises",
    [
        (jwt.PyJWTError("fail"), InvalidTokenError),
        (None, None),
    ],
)
async def test_decode_token_variants(dummy_settings, decode_side_effect, raises):
    with patch(
        "fastcore.security.tokens.jwt.decode", side_effect=decode_side_effect
    ) if decode_side_effect else patch(
        "fastcore.security.tokens.jwt.decode", return_value={"sub": 26}
    ):
        if raises:
            with pytest.raises(raises):
                await decode_token("badtoken")
        else:
            payload = decode_token("sometoken")
            assert payload["sub"] == 26


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,revoked,raises",
    [
        ({"jti": "id1", "type": TokenType.ACCESS, "sub": 26}, False, None),
        ({"jti": "id1", "type": "WRONG", "sub": 26}, False, InvalidTokenError),
        ({"jti": "id1", "type": TokenType.ACCESS, "sub": 26}, True, RevokedTokenError),
        ({"jti": "id1", "type": TokenType.ACCESS, "sub": 26}, None, InvalidTokenError),
    ],
)
async def test_validate_token_variants(
    dummy_settings, dummy_session, payload, revoked, raises
):
    with patch("fastcore.security.tokens.jwt.decode", return_value=payload), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=None
        if revoked is None
        else MagicMock(revoked=revoked, updated_at="now"),
    ):
        if raises:
            with pytest.raises(raises):
                await validate_token("token", dummy_session, TokenType.ACCESS)
        else:
            result = await validate_token("token", dummy_session, TokenType.ACCESS)
            assert result["jti"] == "id1"


@pytest.mark.asyncio
async def test_validate_token_missing_jti(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        return_value={"type": TokenType.ACCESS, "sub": 26},
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "jti" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_not_found(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        return_value={"jti": "id1", "type": TokenType.ACCESS, "sub": 26},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "not found" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_expired(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode", side_effect=jwt.ExpiredSignatureError()
    ):
        with pytest.raises(ExpiredTokenError):
            await validate_token("token", dummy_session, TokenType.ACCESS)


@pytest.mark.asyncio
async def test_validate_token_invalid_type(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        return_value={"jti": "id1", "type": "WRONG", "sub": 26},
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "invalid token type" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_invalid_audience(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        side_effect=jwt.InvalidAudienceError("bad aud"),
    ):
        with pytest.raises(InvalidTokenError):
            await validate_token("token", dummy_session, TokenType.ACCESS)


@pytest.mark.asyncio
async def test_validate_token_invalid_issuer(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        side_effect=jwt.InvalidIssuerError("bad iss"),
    ):
        with pytest.raises(InvalidTokenError):
            await validate_token("token", dummy_session, TokenType.ACCESS)


@pytest.mark.asyncio
async def test_validate_token_signature_error(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode", side_effect=jwt.PyJWTError("bad sig")
    ):
        with pytest.raises(InvalidTokenError):
            await validate_token("token", dummy_session, TokenType.ACCESS)


# --- Token refresh/revoke tests ---
@pytest.mark.asyncio
async def test_refresh_access_token_success(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        return_value={"sub": 26},
    ), patch(
        "fastcore.security.tokens.service.create_access_token",
        new_callable=AsyncMock,
        return_value="newtoken",
    ):
        token = await refresh_access_token("refresh", dummy_session)
        assert token == "newtoken"


@pytest.mark.asyncio
async def test_refresh_access_token_invalid(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.validate_token",
        new_callable=AsyncMock,
        side_effect=InvalidTokenError("fail"),
    ):
        with pytest.raises(InvalidTokenError):
            await refresh_access_token("refresh", dummy_session)


@pytest.mark.asyncio
async def test_refresh_access_token_missing_sub(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.validate_token",
        new_callable=AsyncMock,
        return_value={},
    ):
        with pytest.raises(InvalidTokenError):
            await refresh_access_token("refresh", dummy_session)


@pytest.mark.asyncio
async def test_refresh_access_token_error_branch(dummy_session):
    from fastcore.security.tokens.service import refresh_access_token

    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        side_effect=Exception("fail-refresh-validate"),
    ):
        with pytest.raises(DBError) as exc:
            await refresh_access_token("refresh", dummy_session)
        assert "Error refreshing access token" in str(exc.value)


@pytest.mark.asyncio
async def test_refresh_access_token_logger_info(dummy_settings, dummy_session):
    # Covers logger.info for successful refresh (service.py:135-137)
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        return_value={"sub": 26},
    ), patch(
        "fastcore.security.tokens.service.create_access_token",
        new_callable=AsyncMock,
        return_value="access_token",
    ) as mock_create_access_token:
        token = await refresh_access_token("refresh", dummy_session)
        assert token == "access_token"
        mock_create_access_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_access_token_error_handling(dummy_session):
    from fastcore.security.tokens.service import refresh_access_token

    # Patch validate_token to raise Exception to hit error branch
    with patch(
        "fastcore.security.tokens.service.validate_token",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError):
            await refresh_access_token("token", dummy_session)


@pytest.mark.asyncio
async def test_revoke_token_success(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.service.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1", "sub": 26},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=False),
    ), patch(
        "fastcore.security.tokens.TokenRepository.revoke_token_for_user",
        new_callable=AsyncMock,
    ) as mock_revoke:
        await revoke_token("token", dummy_session)
        mock_revoke.assert_awaited_once_with(26, "id1")


@pytest.mark.asyncio
async def test_revoke_token_already_revoked(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.service.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1", "sub": 26},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=True),
    ):
        await revoke_token("token", dummy_session)


@pytest.mark.asyncio
async def test_revoke_token_invalid_token(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.decode_token", new_callable=AsyncMock, return_value={}
    ):
        with pytest.raises(InvalidTokenError):
            await revoke_token("token", dummy_session)


@pytest.mark.asyncio
async def test_revoke_token_not_found(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1", "sub": 26},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(InvalidTokenError):
            await revoke_token("token", dummy_session)


@pytest.mark.asyncio
async def test_revoke_token_db_error(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.service.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1", "sub": 26},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError):
            await revoke_token("token", dummy_session)


@pytest.mark.asyncio
async def test_revoke_token_flush_db_error(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.service.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1", "sub": 26},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=False),
    ), patch(
        "fastcore.security.tokens.TokenRepository.revoke_token_for_user",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError):
            await revoke_token("token", dummy_session)


@pytest.mark.asyncio
async def test_revoke_token_error_branch(dummy_session):
    from fastcore.security.tokens.service import revoke_token

    with patch(
        "fastcore.security.tokens.service.decode_token",
        new_callable=AsyncMock,
        side_effect=Exception("fail-decode"),
    ):
        with pytest.raises(DBError) as exc:
            await revoke_token("token", dummy_session)
        assert "Error revoking token" in str(exc.value)


@pytest.mark.asyncio
async def test_revoke_token_error_handling(dummy_session):
    from fastcore.security.tokens.service import revoke_token

    # Patch decode_token to raise Exception to hit error branch
    with patch(
        "fastcore.security.tokens.service.decode_token",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError):
            await revoke_token("token", dummy_session)


@pytest.mark.asyncio
async def test_revoke_token_logger_info_branches(dummy_settings, dummy_session):
    # Covers logger.info for already revoked and successfully revoked (service.py:147, 167)
    # Already revoked
    with patch(
        "fastcore.security.tokens.service.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1", "sub": 26},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=True),
    ):
        await revoke_token("token", dummy_session)
    # Successfully revoked
    with patch(
        "fastcore.security.tokens.service.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id2", "sub": 27},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=False),
    ), patch(
        "fastcore.security.tokens.TokenRepository.revoke_token_for_user",
        new_callable=AsyncMock,
    ):
        await revoke_token("token", dummy_session)


@pytest.mark.asyncio
async def test_utils_validate_jwt_stateless_error_branch(dummy_settings):
    from fastcore.security.tokens.utils import validate_jwt_stateless

    with patch(
        "fastcore.security.tokens.utils.jwt.decode",
        side_effect=jwt.PyJWTError("fail-validate"),
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await validate_jwt_stateless("token", None)
        assert "Invalid token signature or format" in str(exc.value)


@pytest.mark.asyncio
async def test_utils_validate_jwt_stateless_success(dummy_settings):
    from fastcore.security.tokens.utils import validate_jwt_stateless

    with patch(
        "fastcore.security.tokens.utils.jwt.decode",
        return_value={"jti": "id1", "sub": 1, "type": TokenType.ACCESS},
    ):
        payload = await validate_jwt_stateless("token", TokenType.ACCESS)
        assert payload["jti"] == "id1"


@pytest.mark.asyncio
async def test_utils_validate_jwt_stateless_pyjwt_error(dummy_settings):
    from fastcore.security.tokens.utils import validate_jwt_stateless

    with patch(
        "fastcore.security.tokens.utils.jwt.decode", side_effect=jwt.PyJWTError("fail")
    ):
        with pytest.raises(InvalidTokenError):
            await validate_jwt_stateless("token", None)


def test_token_model_repr_and_properties():
    from datetime import datetime, timedelta, timezone

    from fastcore.security.tokens.models import Token, TokenType

    token = Token(
        token_id="abc",
        token_type=TokenType.ACCESS,
        revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        user_id=1,
    )
    # __repr__
    assert "Token" in repr(token)
    # is_expired (not expired)
    assert token.is_expired is False
    # is_valid (not revoked, not expired)
    assert token.is_valid is True
    # Expired token
    expired_token = Token(
        token_id="def",
        token_type=TokenType.REFRESH,
        revoked=False,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        user_id=2,
    )
    assert expired_token.is_expired is True
    # Not valid if revoked
    revoked_token = Token(
        token_id="ghi",
        token_type=TokenType.ACCESS,
        revoked=True,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        user_id=3,
    )
    assert revoked_token.is_valid is False


@pytest.mark.asyncio
async def test_revoke_all_tokens_for_user_success():
    session = AsyncMock()
    repo_mock = AsyncMock()
    with patch(
        "fastcore.security.tokens.service.TokenRepository", return_value=repo_mock
    ):
        await revoke_all_tokens_for_user(123, session)
        repo_mock.revoke_all_for_user.assert_awaited_once_with(123)
        session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_all_tokens_for_user_error():
    session = AsyncMock()
    repo_mock = AsyncMock()
    repo_mock.revoke_all_for_user.side_effect = Exception("fail")
    with patch(
        "fastcore.security.tokens.service.TokenRepository", return_value=repo_mock
    ):
        with patch.object(session, "rollback", new_callable=AsyncMock) as rollback_mock:
            with pytest.raises(Exception):
                await revoke_all_tokens_for_user(123, session)
            rollback_mock.assert_awaited_once()
