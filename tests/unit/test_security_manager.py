"""
Unit tests for security.manager module.
Covers: setup_security and get_security_status.
"""
from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi import FastAPI

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
        "src.security.manager.ensure_logger", return_value=MagicMock()
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
        app.dependency_overrides = {}
        import asyncio

        asyncio.run(handler())
        assert manager.security_initialized is True
    # Simulate shutdown
    for handler in app.router.on_shutdown:
        manager.security_initialized = True
        import asyncio

        asyncio.run(handler())
        assert manager.security_initialized is False
