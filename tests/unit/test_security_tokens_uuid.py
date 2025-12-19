"""
Unit tests for UUID Token Service.

Covers specific logic for UUID-based token operations using the functional API.
Verifies that the public functions correctly delegate to the internal singleton instance.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastcore.errors.exceptions import DBError, InvalidTokenError, RevokedTokenError
from fastcore.security.tokens.models import TokenType
from fastcore.security.tokens.uuid import service as uuid_service_module
from fastcore.security.tokens.uuid.models import UUIDToken
from fastcore.security.tokens.uuid.repository import UUIDTokenRepository
from fastcore.security.tokens.uuid.service import _service_impl

# --- Fixtures ---


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# --- Initialization / Wiring Tests ---


def test_internal_wiring():
    """
    Ensure the internal singleton service is initialized with correct UUID models and repos.
    This verifies that the Functional API is backed by the correct logic.
    """
    assert _service_impl.model_cls is UUIDToken
    assert _service_impl.repo_cls is UUIDTokenRepository


# --- Happy Path Tests (Normal Akış) ---


@pytest.mark.asyncio
async def test_uuid_create_token_flow(mock_session):
    """Test creating a token preserves the UUID user_id type via functional API."""
    user_id = str(uuid.uuid4())
    data = {"sub": user_id}

    # Internal singleton'ın miras aldığı base metodu mockluyoruz
    with patch(
        "fastcore.security.tokens.base_service.BaseTokenService._create_token_impl",
        new_callable=AsyncMock,
        return_value="valid.jwt.token",
    ) as mock_create:
        # Public API fonksiyonunu çağırıyoruz
        token = await uuid_service_module.create_token(
            data, mock_session, TokenType.ACCESS
        )

        assert token == "valid.jwt.token"

        # KRİTİK KONTROL: Base metoda giden 'sub' verisi hala UUID string mi?
        # (Legacy sistemde int'e çevriliyordu, burada string kalmalı)
        call_args = mock_create.call_args
        passed_data = call_args[0][0]  # İlk argümanın (data) içeriği
        assert passed_data["sub"] == user_id
        assert isinstance(passed_data["sub"], str)


@pytest.mark.asyncio
async def test_uuid_revoke_all_tokens_with_string(mock_session):
    """Test revoking all tokens uses UUID string for user_id."""
    user_id = str(uuid.uuid4())

    # Repository metodunu mockluyoruz
    with patch.object(
        UUIDTokenRepository, "revoke_all_for_user", new_callable=AsyncMock
    ) as mock_revoke:
        await uuid_service_module.revoke_all_tokens_for_user(user_id, mock_session)

        # Repo'ya giden user_id string (UUID) olmalı
        mock_revoke.assert_awaited_once_with(user_id)
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_uuid_revoke_with_uuid_object(mock_session):
    """
    KRİTİK TEST: Fonksiyona uuid.UUID nesnesi verilirse,
    string'e çevrilip servise iletildiğini doğrular.
    """
    user_uuid_obj = uuid.uuid4()
    expected_str = str(user_uuid_obj)

    # Repository metodunu mockluyoruz
    with patch.object(
        UUIDTokenRepository, "revoke_all_for_user", new_callable=AsyncMock
    ) as mock_revoke:
        # Fonksiyona OBJECT olarak veriyoruz
        await uuid_service_module.revoke_all_tokens_for_user(
            user_uuid_obj, mock_session
        )

        # Repo'ya STRING olarak gitmiş olmalı
        mock_revoke.assert_awaited_once_with(expected_str)
        mock_session.commit.assert_awaited_once()


# --- Edge Case Tests (Köşe Durumları & Hatalar) ---


@pytest.mark.asyncio
async def test_uuid_validate_token_revoked(mock_session):
    """Edge Case: Valid signature but token is revoked in DB."""
    token = "revoked.jwt.token"

    with patch(
        "fastcore.security.tokens.base_service.validate_jwt_stateless",
        return_value={"jti": "uuid-jti", "sub": "uuid-user"},
    ), patch.object(
        UUIDTokenRepository,
        "get_by_token_id",
        new_callable=AsyncMock,
        # DB'den revoked=True dönüyor
        return_value=MagicMock(revoked=True),
    ):
        with pytest.raises(RevokedTokenError):
            await uuid_service_module.validate_token(token, mock_session)


@pytest.mark.asyncio
async def test_uuid_validate_token_not_found(mock_session):
    """Edge Case: Valid signature but token not found in DB."""
    token = "missing.jwt.token"

    with patch(
        "fastcore.security.tokens.base_service.validate_jwt_stateless",
        return_value={"jti": "uuid-jti", "sub": "uuid-user"},
    ), patch.object(
        UUIDTokenRepository,
        "get_by_token_id",
        new_callable=AsyncMock,
        # DB'den None dönüyor
        return_value=None,
    ):
        with pytest.raises(InvalidTokenError) as exc:
            await uuid_service_module.validate_token(token, mock_session)
        assert "not found" in str(exc.value)


@pytest.mark.asyncio
async def test_uuid_refresh_flow_success(mock_session):
    """Test refreshing an access token using a valid UUID refresh token via functional API."""
    refresh_token = "valid.refresh.token"
    user_id = str(uuid.uuid4())

    # 1. Validate çağrısını mockla (Başarılı)
    # 2. Repo kontrolünü mockla (Revoke edilmemiş)
    # 3. Create çağrısını mockla (Yeni token üret)
    with patch(
        "fastcore.security.tokens.base_service.validate_jwt_stateless",
        return_value={"jti": "old-jti", "sub": user_id, "type": "refresh"},
    ), patch.object(
        UUIDTokenRepository,
        "get_by_token_id",
        new_callable=AsyncMock,
        return_value=MagicMock(revoked=False),
    ), patch(
        "fastcore.security.tokens.base_service.BaseTokenService._create_token_impl",
        new_callable=AsyncMock,
        return_value="new.access.token",
    ):
        new_token = await uuid_service_module.refresh_access_token(
            refresh_token, mock_session
        )
        assert new_token == "new.access.token"


@pytest.mark.asyncio
async def test_uuid_db_error_handling(mock_session):
    """Edge Case: Database fails during token creation via functional API."""
    user_id = str(uuid.uuid4())
    data = {"sub": user_id}

    # Create metodunun içindeki repo.create çağrısında hata fırlatıyoruz
    # Bunun için _create_token_impl'i değil, onun çağırdığı repo'yu mocklamak daha gerçekçi olur
    # AMA base_service içindeki logic'i test etmek için BaseService._create_token_impl'e side_effect verebiliriz
    # Veya direkt repo.create mocklayabiliriz. BaseService testinde repo mocklamıştık.
    # Burada servisin hata fırlatmasını test ediyoruz.

    with patch(
        "fastcore.security.tokens.base_service.BaseTokenService._create_token_impl",
        side_effect=DBError("Connection failed"),
    ):
        with pytest.raises(DBError):
            await uuid_service_module.create_token(data, mock_session)
