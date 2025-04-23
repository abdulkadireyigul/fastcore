"""
Unit tests for the config module.

These tests cover:
- Default and environment-based settings loading
- JWT secret key logic (auto-generation, required in production)
- Field validators for JWT audience and allowed audiences
- Environment selection logic (development, testing, production)
- Edge cases for explicit values

All tests use fixtures and monkeypatching to ensure isolation and avoid code duplication.
"""

import pytest

from src.config.base import BaseAppSettings


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
    from src.config.settings import get_settings as gs

    settings = gs()
    assert settings.__class__.__name__ == "TestingSettings"
    monkeypatch.setenv("APP_ENV", "production")
    settings = gs()
    assert settings.__class__.__name__ == "ProductionSettings"
    monkeypatch.setenv("APP_ENV", "development")
    settings = gs()
    assert settings.__class__.__name__ == "DevelopmentSettings"
