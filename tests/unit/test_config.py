"""
Unit tests for the config module.

These tests cover:
- Default and environment-based settings loading
- JWT secret key logic (auto-generation, required in production)
- Field validators for JWT audience and allowed audiences
- Environment selection logic (development, testing, production)
- Edge cases for explicit values
- Validators for DATABASE_URL and CACHE_URL

All tests use fixtures and monkeypatching to ensure isolation and avoid code duplication.
"""

import pytest

from fastcore.config.base import BaseAppSettings


@pytest.fixture(autouse=True)
def set_required_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET_KEY", "dummykey")


def test_base_app_settings_defaults():
    settings = BaseAppSettings(
        DEBUG=True, JWT_SECRET_KEY="testkey", DATABASE_URL="sqlite:///:memory:"
    )
    assert settings.APP_NAME == "FastCore"
    assert settings.DEBUG is True
    assert settings.CACHE_URL.startswith("redis://")
    assert settings.JWT_SECRET_KEY == "testkey"


def test_env_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "MyApp")
    monkeypatch.setenv("DEBUG", "True")
    monkeypatch.setenv("JWT_SECRET_KEY", "envkey")
    settings = BaseAppSettings()
    assert settings.APP_NAME == "MyApp"
    assert settings.DEBUG is True
    assert settings.JWT_SECRET_KEY == "envkey"


def test_jwt_secret_key_auto_generate(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    settings = BaseAppSettings(DEBUG=True, DATABASE_URL="sqlite:///:memory:")
    assert isinstance(settings.JWT_SECRET_KEY, str)
    assert len(settings.JWT_SECRET_KEY) == 64


def test_jwt_secret_key_required_in_production(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValueError):
        BaseAppSettings(DEBUG=False, DATABASE_URL="sqlite:///:memory:")


def test_jwt_audience_and_allowed_audiences():
    s = BaseAppSettings(
        DEBUG=True,
        JWT_SECRET_KEY="x",
        JWT_AUDIENCE=None,
        JWT_ALLOWED_AUDIENCES=None,
        DATABASE_URL="sqlite:///:memory:",
    )
    assert s.JWT_AUDIENCE == s.APP_NAME.lower()
    assert s.JWT_AUDIENCE in s.JWT_ALLOWED_AUDIENCES


def test_jwt_audience_explicit_value():
    s = BaseAppSettings(
        DEBUG=True,
        JWT_SECRET_KEY="x",
        JWT_AUDIENCE="explicit_aud",
        JWT_ISSUER="explicit_iss",
        JWT_ALLOWED_AUDIENCES=["aud1", "aud2"],
        DATABASE_URL="sqlite:///:memory:",
    )
    assert s.JWT_AUDIENCE == "explicit_aud"
    assert s.JWT_ISSUER == "explicit_iss"
    assert s.JWT_ALLOWED_AUDIENCES == ["aud1", "aud2"]


def test_get_settings_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    from fastcore.config.settings import get_settings as gs

    settings = gs()
    assert settings.__class__.__name__ == "TestingSettings"
    monkeypatch.setenv("APP_ENV", "production")
    settings = gs()
    assert settings.__class__.__name__ == "ProductionSettings"
    monkeypatch.setenv("APP_ENV", "development")
    settings = gs()
    assert settings.__class__.__name__ == "DevelopmentSettings"


# DATABASE_URL validator tests
def test_database_url_asyncpg_required():
    with pytest.raises(
        ValueError, match=r"DATABASE_URL must start with 'postgresql\+asyncpg://'"
    ):
        BaseAppSettings(
            DATABASE_URL="postgresql://user:pass@localhost/db",
            CACHE_URL="redis://localhost:6379/0",
            JWT_SECRET_KEY="x",
        )


def test_database_url_asyncpg_valid():
    settings = BaseAppSettings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        CACHE_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="x",
    )
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")


# CACHE_URL validator tests
def test_cache_url_redis_required():
    with pytest.raises(ValueError, match="CACHE_URL must start with 'redis://'"):
        BaseAppSettings(
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
            CACHE_URL="http://localhost:6379/0",
            JWT_SECRET_KEY="x",
        )


def test_cache_url_redis_valid():
    settings = BaseAppSettings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        CACHE_URL="redis://localhost:6379/0",
        JWT_SECRET_KEY="x",
    )
    assert settings.CACHE_URL.startswith("redis://")
    settings2 = BaseAppSettings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        CACHE_URL="rediss://localhost:6379/0",
        JWT_SECRET_KEY="x",
    )
    assert settings2.CACHE_URL.startswith("rediss://")
