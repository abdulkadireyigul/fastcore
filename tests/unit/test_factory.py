"""
Unit tests for the factory module.

Covers:
- FastAPI application configuration via configure_app
- Settings loading and defaulting
- All setup functions (errors, cache, db, security, middleware, monitoring)
- Logging and app attribute assignment

All tests use mocks to isolate FastAPI app, settings, and setup dependencies.
"""

from unittest.mock import MagicMock

from fastapi import FastAPI

from fastcore.factory.app import configure_app


def test_configure_app_sets_attributes_and_calls_setups(monkeypatch):
    app = MagicMock(spec=FastAPI)
    app.title = ""
    app.version = ""
    app.debug = False
    settings = MagicMock()
    settings.APP_NAME = "TestApp"
    settings.VERSION = "1.2.3"
    settings.DEBUG = True
    called = {}
    monkeypatch.setattr(
        "src.factory.app.setup_errors",
        lambda *a, **kw: called.setdefault("errors", True),
    )
    monkeypatch.setattr(
        "src.factory.app.setup_cache", lambda *a, **kw: called.setdefault("cache", True)
    )
    monkeypatch.setattr(
        "src.factory.app.setup_db", lambda *a, **kw: called.setdefault("db", True)
    )
    monkeypatch.setattr(
        "src.factory.app.setup_security",
        lambda *a, **kw: called.setdefault("security", True),
    )
    monkeypatch.setattr(
        "src.factory.app.setup_middlewares",
        lambda *a, **kw: called.setdefault("middlewares", True),
    )
    monkeypatch.setattr(
        "src.factory.app.setup_monitoring",
        lambda *a, **kw: called.setdefault("monitoring", True),
    )
    monkeypatch.setattr("src.factory.app.ensure_logger", lambda *a, **kw: MagicMock())
    configure_app(app, settings)
    assert app.title == "TestApp"
    assert app.version == "1.2.3"
    assert app.debug is True
    for key in ["errors", "cache", "db", "security", "middlewares", "monitoring"]:
        assert called[key]


def test_configure_app_uses_default_settings(monkeypatch):
    app = MagicMock(spec=FastAPI)
    app.title = ""
    app.version = ""
    app.debug = False
    settings = MagicMock()
    settings.APP_NAME = "TestApp"
    settings.VERSION = "1.2.3"
    settings.DEBUG = True
    monkeypatch.setattr("src.factory.app.get_settings", lambda: settings)
    monkeypatch.setattr("src.factory.app.setup_errors", lambda *a, **kw: None)
    monkeypatch.setattr("src.factory.app.setup_cache", lambda *a, **kw: None)
    monkeypatch.setattr("src.factory.app.setup_db", lambda *a, **kw: None)
    monkeypatch.setattr("src.factory.app.setup_security", lambda *a, **kw: None)
    monkeypatch.setattr("src.factory.app.setup_middlewares", lambda *a, **kw: None)
    monkeypatch.setattr("src.factory.app.setup_monitoring", lambda *a, **kw: None)
    monkeypatch.setattr("src.factory.app.ensure_logger", lambda *a, **kw: MagicMock())
    configure_app(app)
    assert app.title == "TestApp"
    assert app.version == "1.2.3"
    assert app.debug is True
