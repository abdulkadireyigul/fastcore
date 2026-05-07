"""
Unit tests for security.manager module.
Covers: setup_security and get_security_status.
"""
from typing import Optional
from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi import FastAPI

from fastcore.config.base import BaseAppSettings
from fastcore.security import manager


def test_get_security_status_initialized(monkeypatch):
    monkeypatch.setattr(manager, "security_initialized", True)
    assert manager.get_security_status() is True


def test_get_security_status_not_initialized(monkeypatch):
    monkeypatch.setattr(manager, "security_initialized", False)
    with pytest.raises(RuntimeError):
        manager.get_security_status()


def test_setup_security_adds_handlers():
    app = MagicMock(spec=FastAPI)
    settings = MagicMock()
    settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    with patch(
        "fastcore.security.manager.ensure_logger", return_value=MagicMock()
    ) as mock_logger:
        manager.setup_security(app, settings)
        app.add_event_handler.assert_any_call("startup", ANY)
        app.add_event_handler.assert_any_call("shutdown", ANY)


def test_setup_security_startup_and_shutdown(monkeypatch):
    app = FastAPI()
    settings = MagicMock()
    settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    log = MagicMock()
    monkeypatch.setattr(manager, "ensure_logger", lambda *a, **kw: log)
    manager.setup_security(app, settings)
    # Simulate startup
    for handler in app.router.on_startup:
        manager.security_initialized = False
        manager.security_settings = None
        app.dependency_overrides = {}
        import asyncio

        asyncio.run(handler())
        assert manager.security_initialized is True
        assert manager.security_settings == settings
    # Simulate shutdown
    for handler in app.router.on_shutdown:
        manager.security_initialized = True
        manager.security_settings = settings
        import asyncio

        asyncio.run(handler())
        assert manager.security_initialized is False
        assert manager.security_settings is None


def test_setup_security_with_custom_settings():
    """
    Test that setup_security properly uses custom settings passed to it.
    """
    app = FastAPI()

    # Create custom settings with unique values we can verify
    class CustomSettings(BaseAppSettings):
        APP_NAME: str = "CustomApp"
        APP_ENV: str = "testing"
        DATABASE_URL: str = "sqlite:///./custom.db"

        # Custom JWT settings different from defaults
        JWT_SECRET_KEY: str = "custom-secret-key"
        JWT_ALGORITHM: str = "HS512"  # Different from default HS256
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Different from default
        JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 14  # Different from default
        JWT_AUDIENCE: Optional[str] = "custom-audience"
        JWT_ISSUER: Optional[str] = "custom-issuer"

    custom_settings = CustomSettings()

    # Setup security with our custom settings
    manager.setup_security(app, custom_settings)

    # Get the settings currently being used by security module
    current_settings = manager.get_security_settings()

    # Verify that security module is using our custom values
    assert current_settings.JWT_SECRET_KEY == "custom-secret-key"
    assert current_settings.JWT_ALGORITHM == "HS512"
    assert current_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60
    assert current_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 14
    assert current_settings.JWT_AUDIENCE == "custom-audience"
    assert current_settings.JWT_ISSUER == "custom-issuer"
