"""
Unit tests for security.tokens module.
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
from fastcore.security.models import Token, TokenType
from fastcore.security.tokens import (
    TokenRepository,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    refresh_access_token,
    revoke_token,
    validate_token,
)


@pytest.mark.asyncio
async def test_token_repository_get_by_token_id_success(dummy_session):
    with patch("fastcore.security.tokens.select") as mock_select:
        repo = TokenRepository(Token, dummy_session)
        dummy_token = MagicMock(token_id="abc")
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = dummy_token
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        dummy_session.execute = AsyncMock(return_value=mock_result)
        token = await repo.get_by_token_id("abc")
        assert token.token_id == "abc"
        dummy_session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_token_repository_get_by_token_id_db_error(dummy_session):
    with patch("fastcore.security.tokens.select") as mock_select:
        repo = TokenRepository(Token, dummy_session)
        dummy_session.execute = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(DBError) as exc:
            await repo.get_by_token_id("abc")
        assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_token_repository_revoke_token(dummy_session):
    with patch("fastcore.security.tokens.select") as mock_select:
        repo = TokenRepository(Token, dummy_session)
        dummy = MagicMock(token_id="abc", revoked=False)
        repo.get_by_token_id = AsyncMock(return_value=dummy)
        dummy_session.flush.return_value = None
        await repo.revoke_token("abc")
        assert dummy.revoked is True
        dummy_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_token_repository_revoke_all_user_tokens(dummy_session):
    with patch("fastcore.security.tokens.select") as mock_select:
        repo = TokenRepository(Token, dummy_session)
        dummy1 = MagicMock(token_id="a", revoked=False)
        dummy2 = MagicMock(token_id="b", revoked=False)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [dummy1, dummy2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        dummy_session.execute = AsyncMock(return_value=mock_result)
        dummy_session.flush.return_value = None
        await repo.revoke_all_user_tokens("user1")
        assert dummy1.revoked is True and dummy2.revoked is True
        dummy_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_token_repository_revoke_all_user_tokens_db_error(dummy_session):
    with patch("fastcore.security.tokens.select") as mock_select:
        repo = TokenRepository(Token, dummy_session)
        dummy_session.execute = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(DBError) as exc:
            await repo.revoke_all_user_tokens("user1")
        assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_token_repository_get_refresh_token_for_user(dummy_session):
    with patch("fastcore.security.tokens.select") as mock_select:
        repo = TokenRepository(Token, dummy_session)
        now = datetime.now(timezone.utc)
        dummy = MagicMock(
            token_id="abc",
            token_type=TokenType.REFRESH,
            revoked=False,
            expires_at=now + timedelta(days=1),
            created_at=now,
        )
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = dummy
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        dummy_session.execute = AsyncMock(return_value=mock_result)
        token = await repo.get_refresh_token_for_user("user1")
        assert token.token_id == "abc"
        dummy_session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_token_repository_get_refresh_token_for_user_db_error(dummy_session):
    with patch("fastcore.security.tokens.select") as mock_select:
        repo = TokenRepository(Token, dummy_session)
        dummy_session.execute = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(DBError) as exc:
            await repo.get_refresh_token_for_user("user1")
        assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_create_access_token_success(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.encode", return_value="jwt_token"
    ) as mock_encode, patch(
        "fastcore.security.tokens.TokenRepository.create", new_callable=AsyncMock
    ) as mock_create:
        token = await create_access_token({"sub": "user1"}, dummy_session)
        assert token == "jwt_token"
        mock_encode.assert_called_once()
        mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_access_token_db_error(dummy_settings, dummy_session):
    with patch("fastcore.security.tokens.jwt.encode", return_value="jwt_token"), patch(
        "fastcore.security.tokens.TokenRepository.create",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError) as exc:
            await create_access_token({"sub": "user1"}, dummy_session)
        assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_create_refresh_token_success(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.encode", return_value="jwt_refresh"
    ) as mock_encode, patch(
        "fastcore.security.tokens.TokenRepository.create", new_callable=AsyncMock
    ) as mock_create:
        token = await create_refresh_token({"sub": "user1"}, dummy_session)
        assert token == "jwt_refresh"
        mock_encode.assert_called_once()
        mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_refresh_token_db_error(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.encode", return_value="jwt_refresh"
    ), patch(
        "fastcore.security.tokens.TokenRepository.create",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError) as exc:
            await create_refresh_token({"sub": "user1"}, dummy_session)
        assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_create_token_pair_success(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.create_access_token",
        new_callable=AsyncMock,
        return_value="access",
    ) as mock_access, patch(
        "fastcore.security.tokens.create_refresh_token",
        new_callable=AsyncMock,
        return_value="refresh",
    ) as mock_refresh:
        pair = await create_token_pair({"sub": "user1"}, dummy_session)
        assert pair["access_token"] == "access"
        assert pair["refresh_token"] == "refresh"
        assert pair["token_type"] == "bearer"
        mock_access.assert_awaited_once()
        mock_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_decode_token_success(dummy_settings):
    with patch("fastcore.security.tokens.jwt.decode", return_value={"sub": "user1"}):
        payload = await decode_token("sometoken")
        assert payload["sub"] == "user1"


@pytest.mark.asyncio
async def test_decode_token_invalid(dummy_settings):
    with patch(
        "fastcore.security.tokens.jwt.decode", side_effect=jwt.PyJWTError("fail")
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await decode_token("badtoken")
        # assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_validate_token_success(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        return_value={"jti": "id1", "type": TokenType.ACCESS, "sub": "user1"},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=False),
    ):
        payload = await validate_token("token", dummy_session, TokenType.ACCESS)
        assert payload["jti"] == "id1"


@pytest.mark.asyncio
async def test_validate_token_missing_jti(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        return_value={"type": TokenType.ACCESS, "sub": "user1"},
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "jti" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_not_found(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        return_value={"jti": "id1", "type": TokenType.ACCESS, "sub": "user1"},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "not found" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_revoked(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        return_value={"jti": "id1", "type": TokenType.ACCESS, "sub": "user1"},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=True, updated_at="now"),
    ):
        with pytest.raises(RevokedTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "revoked" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_expired(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode", side_effect=jwt.ExpiredSignatureError()
    ):
        with pytest.raises(ExpiredTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "expired" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_invalid_type(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        return_value={"jti": "id1", "type": "WRONG", "sub": "user1"},
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
        with pytest.raises(InvalidTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "audience" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_invalid_issuer(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode",
        side_effect=jwt.InvalidIssuerError("bad iss"),
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert "issuer" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_validate_token_signature_error(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.jwt.decode", side_effect=jwt.PyJWTError("bad sig")
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await validate_token("token", dummy_session, TokenType.ACCESS)
        assert (
            "signature" in str(exc.value).lower() or "format" in str(exc.value).lower()
        )


@pytest.mark.asyncio
async def test_refresh_access_token_success(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.validate_token",
        new_callable=AsyncMock,
        return_value={"sub": "user1"},
    ), patch(
        "fastcore.security.tokens.create_access_token",
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
        with pytest.raises(InvalidTokenError) as exc:
            await refresh_access_token("refresh", dummy_session)
        assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_refresh_access_token_missing_sub(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.validate_token",
        new_callable=AsyncMock,
        return_value={},
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await refresh_access_token("refresh", dummy_session)
        assert "invalid token content" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_revoke_token_success(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1"},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=False),
    ), patch(
        "fastcore.security.tokens.TokenRepository.revoke_token", new_callable=AsyncMock
    ) as mock_revoke:
        await revoke_token("token", dummy_session)
        mock_revoke.assert_awaited_once_with("id1")


@pytest.mark.asyncio
async def test_revoke_token_already_revoked(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1"},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=True),
    ):
        # Should not raise, just log and return
        await revoke_token("token", dummy_session)


@pytest.mark.asyncio
async def test_revoke_token_invalid_token(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.decode_token", new_callable=AsyncMock, return_value={}
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await revoke_token("token", dummy_session)
        assert "jti" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_revoke_token_not_found(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1"},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await revoke_token("token", dummy_session)
        assert "not found" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_revoke_token_db_error(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1"},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError) as exc:
            await revoke_token("token", dummy_session)
        # assert "fail" in str(exc.value)


@pytest.mark.asyncio
async def test_revoke_token_flush_db_error(dummy_settings, dummy_session):
    with patch(
        "fastcore.security.tokens.decode_token",
        new_callable=AsyncMock,
        return_value={"jti": "id1"},
    ), patch(
        "fastcore.security.tokens.TokenRepository.get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=False),
    ), patch(
        "fastcore.security.tokens.TokenRepository.revoke_token",
        new_callable=AsyncMock,
        side_effect=Exception("fail"),
    ):
        with pytest.raises(DBError) as exc:
            await revoke_token("token", dummy_session)
        # assert "fail" in str(exc.value)
