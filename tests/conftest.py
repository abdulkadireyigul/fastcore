from unittest.mock import AsyncMock

import pytest


# Example: shared fixture for environment variable cleanup
def pytest_configure(config):
    # Called before any tests are run
    pass


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Automatically clear certain environment variables before each test if needed
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    yield
    # No teardown needed, monkeypatch handles it


@pytest.fixture
def dummy_session():
    """Reusable async session mock for DB operations."""
    return AsyncMock()


@pytest.fixture
def dummy_settings(monkeypatch):
    """Reusable dummy settings for security tests."""

    class DummySettings:
        JWT_SECRET_KEY = "secret"
        JWT_ALGORITHM = "HS256"
        JWT_AUDIENCE = "aud"
        JWT_ISSUER = "iss"
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
        JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
        JWT_ALLOWED_AUDIENCES = ["aud"]

    monkeypatch.setattr("src.security.tokens.get_settings", lambda: DummySettings())
    return DummySettings()


# Helper for consistent HTTPException assertions
def assert_http_exc(exc, status, msg):
    assert exc.value.status_code == status
    assert msg in str(exc.value.detail).lower()


# Add more shared fixtures as your test suite grows
