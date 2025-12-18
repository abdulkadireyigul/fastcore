"""
Unit tests for UUID Token Service.
Covers specific logic for UUID-based token operations, inheriting from BaseService.
"""

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastcore.errors.exceptions import DBError, InvalidTokenError, RevokedTokenError
from fastcore.security.tokens.models import TokenType
from fastcore.security.tokens.uuid.models import UUIDToken
from fastcore.security.tokens.uuid.repository import UUIDTokenRepository
from fastcore.security.tokens.uuid.service import UUIDTokenService


# --- Fixtures ---
@pytest.fixture
def uuid_service():
    return UUIDTokenService()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# --- Initialization Tests ---
def test_uuid_service_initialization(uuid_service):
    """Ensure the service is initialized with correct UUID models and repos."""
    assert uuid_service.model_cls == UUIDToken
    assert uuid_service.repo_cls == UUIDTokenRepository


# --- Happy Path Tests (Normal Akış) ---


@pytest.mark.asyncio
async def test_uuid_create_token_flow(uuid_service, mock_session):
    """Test creating a token preserves the UUID user_id type."""
    user_id = str(uuid.uuid4())
    data = {"sub": user_id}

    # Internal impl'i mockluyoruz ki DB'ye gitmesin ama akışı test edelim
    with patch(
        "fastcore.security.tokens.base_service.BaseTokenService._create_token_impl",
        new_callable=AsyncMock,
        return_value="valid.jwt.token",
    ) as mock_create:
        token = await uuid_service.create_token(data, mock_session, TokenType.ACCESS)

        assert token == "valid.jwt.token"

        # KRİTİK KONTROL: Base metoda giden 'sub' verisi hala UUID string mi?
        # (Legacy sistemde int'e çevriliyordu, burada string kalmalı)
        call_args = mock_create.call_args
        passed_data = call_args[0][0]  # İlk argümanın (data) içeriği
        assert passed_data["sub"] == user_id
        assert isinstance(passed_data["sub"], str)


@pytest.mark.asyncio
async def test_uuid_revoke_all_tokens(uuid_service, mock_session):
    """Test revoking all tokens uses UUID string for user_id."""
    user_id = str(uuid.uuid4())

    # Repository metodunu mockluyoruz
    with patch.object(
        UUIDTokenRepository, "revoke_all_for_user", new_callable=AsyncMock
    ) as mock_revoke:
        await uuid_service.revoke_all_tokens_for_user(user_id, mock_session)

        # Repo'ya giden user_id string (UUID) olmalı
        mock_revoke.assert_awaited_once_with(user_id)
        mock_session.commit.assert_awaited_once()


# --- Edge Case Tests (Köşe Durumları & Hatalar) ---


@pytest.mark.asyncio
async def test_uuid_validate_token_revoked(uuid_service, mock_session):
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
            await uuid_service.validate_token(token, mock_session)


@pytest.mark.asyncio
async def test_uuid_validate_token_not_found(uuid_service, mock_session):
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
            await uuid_service.validate_token(token, mock_session)
        assert "not found" in str(exc.value)


@pytest.mark.asyncio
async def test_uuid_refresh_flow_success(uuid_service, mock_session):
    """Test refreshing an access token using a valid UUID refresh token."""
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
        new_token = await uuid_service.refresh_access_token(refresh_token, mock_session)
        assert new_token == "new.access.token"


@pytest.mark.asyncio
async def test_uuid_db_error_handling(uuid_service, mock_session):
    """Edge Case: Database fails during token creation."""
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
            await uuid_service.create_token(data, mock_session)
