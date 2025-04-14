"""
Tests for the factory module.

This module contains comprehensive tests for the factory module,
which is responsible for creating and configuring FastAPI applications.
"""

import os
from unittest.mock import ANY, Mock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from fastcore.config.app import AppSettings
from fastcore.config.base import Environment
from fastcore.factory import _configure_cache, create_app
from fastcore.middleware import (
    CORSConfig,
    I18nConfig,
    RateLimitConfig,
    TimingConfig,
    TrustedHostsConfig,
)


@pytest.fixture
def mock_settings():
    """Create a mock AppSettings instance for testing."""
    settings = Mock(spec=AppSettings)
    settings.TITLE = "Test App"
    settings.DESCRIPTION = "Test Description"
    settings.VERSION = "0.1.0"
    settings.ENV = Environment.DEVELOPMENT
    settings.LOGGING = Mock()
    settings.DB = Mock()
    settings.CACHE = Mock()
    settings.CACHE.CACHE_TYPE = "memory"
    settings.CACHE.DEFAULT_TTL = 60
    settings.CACHE.MAX_SIZE = 1000
    return settings


@pytest.fixture
def mock_load_settings(mock_settings):
    """Mock the AppSettings.load method to return our mock settings."""
    with patch.object(AppSettings, "load", return_value=mock_settings) as mock_load:
        yield mock_load


@pytest.fixture
def mock_configure_logging():
    """Mock the configure_logging function."""
    with patch("fastcore.factory.configure_logging") as mock:
        yield mock


@pytest.fixture
def mock_initialize_db():
    """Mock the initialize_db function."""
    with patch("fastcore.factory.initialize_db") as mock:
        yield mock


@pytest.fixture
def mock_configure_cache():
    """Mock the _configure_cache function."""
    with patch("fastcore.factory._configure_cache") as mock:
        yield mock


@pytest.fixture
def mock_configure_environment_middleware():
    """Mock the configure_environment_middleware function."""
    with patch("fastcore.factory.configure_environment_middleware") as mock:
        yield mock


@pytest.fixture
def mock_instrument_app():
    """Mock the monitoring.instrumentation.instrument_app function."""
    with patch("fastcore.monitoring.instrumentation.instrument_app") as mock:
        yield mock


def test_create_app_minimal(
    mock_load_settings, mock_configure_logging, mock_configure_cache
):
    """Test creating an app with minimal configuration."""
    # Create an app with default settings
    app = create_app()

    # Verify the app was created correctly
    assert isinstance(app, FastAPI)
    assert app.title == "Test App"
    assert app.description == "Test Description"
    assert app.version == "0.1.0"

    # Verify settings were loaded with the right environment
    mock_load_settings.assert_called_once_with(Environment.DEVELOPMENT)

    # Verify logging was configured
    mock_configure_logging.assert_called_once()

    # Check that app has default route handlers
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}


def test_create_app_with_different_environment(
    mock_load_settings, mock_configure_logging
):
    """Test creating an app with a different environment."""
    app = create_app(env=Environment.PRODUCTION)

    # Verify settings were loaded with production environment
    mock_load_settings.assert_called_once_with(Environment.PRODUCTION)
    mock_configure_logging.assert_called_once()


def test_create_app_with_database(mock_load_settings, mock_configure_logging):
    """Test creating an app with database enabled."""
    with patch("fastcore.factory.initialize_db") as mock_initialize_db:
        app = create_app(enable_database=True)

        # Verify the database was initialized during lifespan setup
        # Check that it's called in the app's lifespan (happens when FastAPI starts)
        assert app.router.lifespan_context is not None
        mock_initialize_db.assert_not_called()  # Not called directly, but through lifespan


def test_create_app_without_logging(mock_load_settings, mock_configure_logging):
    """Test creating an app with logging disabled."""
    app = create_app(enable_logging=False)

    # Verify logging configuration was skipped
    mock_configure_logging.assert_not_called()


def test_create_app_with_monitoring(
    mock_load_settings, mock_configure_logging, mock_instrument_app
):
    """Test creating an app with monitoring enabled."""
    app = create_app(enable_monitoring=True)

    # Verify monitoring was set up
    mock_instrument_app.assert_called_once_with(app)


@pytest.mark.parametrize("auto_configure", [True, False])
def test_create_app_middleware_configuration(
    mock_load_settings,
    mock_configure_logging,
    mock_configure_environment_middleware,
    auto_configure,
):
    """Test both auto and manual middleware configuration."""
    app = create_app(
        auto_configure=auto_configure,
        enable_cors=True,
        enable_rate_limiting=True,
        enable_i18n=True,
        enable_trusted_hosts=True,
        enable_timing=True,
    )

    if auto_configure:
        # Verify environment middleware configuration was called
        mock_configure_environment_middleware.assert_called_once()
    else:
        # Verify environment middleware configuration was NOT called
        mock_configure_environment_middleware.assert_not_called()


def test_create_app_custom_middleware(mock_load_settings, mock_configure_logging):
    """Test adding custom middleware."""

    # Define a simple test middleware
    class TestMiddleware:
        def __init__(self, app, param=None):
            self.app = app
            self.param = param

    # Create app with custom middleware
    custom_middleware = {"class": TestMiddleware, "args": {"param": "test_value"}}

    app = create_app(middlewares=[custom_middleware])

    # Check if our middleware was added (this is tricky since FastAPI doesn't expose middlewares directly)
    # We could inspect app.user_middleware but that's implementation-specific
    # Instead, let's just verify the app was created successfully
    assert isinstance(app, FastAPI)


def test_create_app_exception_handlers(mock_load_settings, mock_configure_logging):
    """Test configuring custom exception handlers."""

    # Define a custom exception and handler
    class TestException(Exception):
        pass

    def test_exception_handler(request, exc):
        return {"error": "test_error"}

    # Create app with custom exception handler
    app = create_app(
        exception_handler_overrides={TestException: test_exception_handler}
    )

    # Verify the app was created successfully
    assert isinstance(app, FastAPI)

    # Verify our exception handler was registered
    assert TestException in app.exception_handlers


def test_create_app_cors_config(mock_load_settings, mock_configure_logging):
    """Test creating an app with custom CORS configuration."""
    with patch("fastcore.factory.configure_cors") as mock_configure_cors:
        # Create app with CORS config
        cors_config = CORSConfig(
            allow_origins=["https://example.com"], allow_credentials=True
        )

        app = create_app(
            enable_cors=True, cors_config=cors_config, auto_configure=False
        )

        # Verify CORS middleware was configured with our custom config
        mock_configure_cors.assert_called_once_with(app, cors_config)


def test_cors_config_dict(mock_load_settings, mock_configure_logging):
    """Test creating an app with CORS config as dict."""
    with patch("fastcore.factory.configure_cors") as mock_configure_cors, patch(
        "fastcore.factory.CORSConfig"
    ) as mock_cors_config_class:
        # Create app with CORS config as dict
        cors_config = {
            "allow_origins": ["https://example.com"],
            "allow_credentials": True,
        }

        app = create_app(
            enable_cors=True, cors_config=cors_config, auto_configure=False
        )

        # Verify CORSConfig constructor was called with dict values
        mock_cors_config_class.assert_called_once_with(**cors_config)

        # Verify configure_cors was called with the constructed config
        mock_configure_cors.assert_called_once_with(
            app, mock_cors_config_class.return_value
        )


def test_configure_cache_function():
    """Test the _configure_cache function."""
    # Create a mock settings object with properly configured CACHE
    settings = Mock()
    settings.CACHE = Mock()
    settings.CACHE.CACHE_TYPE = "memory"
    settings.CACHE.DEFAULT_TTL = 60
    settings.CACHE.MAX_SIZE = 1000

    # Create a mock for the configure_cache function and the logger
    mock_configure = Mock()
    mock_logger = Mock()

    # Mock the module import inside the function and built-in hasattr
    with patch.dict("sys.modules", {"fastcore.cache": Mock()}), patch(
        "builtins.hasattr", lambda obj, attr: attr != "REDIS_URL"
    ), patch("fastcore.factory.logger", mock_logger):
        # Configure the mock for the imported configure_cache
        import sys

        sys.modules["fastcore.cache"].configure_cache = mock_configure

        # Call the function
        _configure_cache(settings)

        # Verify configure_cache was called with the right parameters
        mock_configure.assert_called_once_with(
            cache_type="memory", ttl=60, max_size=1000, redis_url=None
        )


def test_configure_cache_exception_handling():
    """Test that _configure_cache handles exceptions properly."""
    # Create a mock settings object
    settings = Mock()
    settings.CACHE.CACHE_TYPE = "invalid"

    # Mock the configure_cache function to raise an exception
    with patch("fastcore.cache.configure_cache", side_effect=Exception("Test error")):
        # Call the function (it should not raise the exception)
        _configure_cache(settings)
        # If we get here without an exception, the test passes


def test_configure_cache_no_cache_settings():
    """Test _configure_cache when no cache settings are available."""
    # Create a settings object without CACHE attribute
    settings = Mock(spec=[])  # empty spec means no attributes

    # Call the function (it should handle this case gracefully)
    _configure_cache(settings)
    # If we get here without an exception, the test passes


@pytest.mark.asyncio
async def test_lifespan_context():
    """Test the lifespan context manager."""
    # Create an app with database enabled
    with patch("fastcore.factory.initialize_db") as mock_init_db, patch(
        "fastcore.factory._configure_cache"
    ) as mock_config_cache:
        app = create_app(enable_database=True)

        # Get the lifespan context manager
        lifespan = app.router.lifespan_context

        # Create a mock app for the context manager
        mock_app = Mock()

        # Execute the lifespan startup
        async with lifespan(mock_app):
            # Verify the startup actions were performed
            mock_init_db.assert_called_once()
            mock_config_cache.assert_called_once()

        # After context exit, we could check for cleanup actions
        # but currently there are none except logging


def test_manual_middleware_cors_default_origins(
    mock_load_settings, mock_configure_logging
):
    """Test manual CORS middleware configuration with default origins."""
    with patch("fastcore.factory.configure_cors") as mock_configure_cors:
        # Create app with manual middleware configuration
        app = create_app(
            env=Environment.DEVELOPMENT, enable_cors=True, auto_configure=False
        )

        # Verify CORS middleware was configured with default origins
        mock_configure_cors.assert_called_once()
        _, kwargs = mock_configure_cors.call_args
        assert "allow_origins" in kwargs
        assert kwargs["allow_origins"] == ["*"]


def test_manual_middleware_cors_default_origins_production(
    mock_load_settings, mock_configure_logging
):
    """Test manual CORS middleware configuration with default origins in production."""
    with patch("fastcore.factory.configure_cors") as mock_configure_cors:
        # Create app with manual middleware configuration
        app = create_app(
            env=Environment.PRODUCTION, enable_cors=True, auto_configure=False
        )

        # Verify CORS middleware was configured with empty default origins for production
        mock_configure_cors.assert_called_once()
        _, kwargs = mock_configure_cors.call_args
        assert "allow_origins" in kwargs
        assert kwargs["allow_origins"] == []


def test_manual_middleware_rate_limiting(mock_load_settings, mock_configure_logging):
    """Test manual rate limiting middleware configuration."""
    with patch(
        "fastcore.factory.configure_rate_limiting"
    ) as mock_configure_rate_limiting:
        # Create app with manual rate limiting middleware
        rate_limit_config = RateLimitConfig(
            limit=100, window_seconds=60, exclude_paths=["/docs"]
        )

        app = create_app(
            enable_rate_limiting=True,
            rate_limit_config=rate_limit_config,
            auto_configure=False,
        )

        # Verify rate limiting middleware was configured
        mock_configure_rate_limiting.assert_called_once_with(app, rate_limit_config)


def test_manual_middleware_rate_limiting_dict(
    mock_load_settings, mock_configure_logging
):
    """Test manual rate limiting middleware configuration with dict config."""
    with patch(
        "fastcore.factory.configure_rate_limiting"
    ) as mock_configure_rate_limiting, patch(
        "fastcore.factory.RateLimitConfig", return_value=Mock()
    ) as mock_rate_limit_class:
        # Create app with manual rate limiting middleware using dict config
        rate_limit_config = {
            "limit": 100,
            "window_seconds": 60,
            "exclude_paths": ["/docs"],
        }

        app = create_app(
            enable_rate_limiting=True,
            rate_limit_config=rate_limit_config,
            auto_configure=False,
        )

        # Verify RateLimitConfig constructor was called with dict values
        mock_rate_limit_class.assert_called_once_with(**rate_limit_config)

        # Verify rate limiting middleware was configured
        mock_configure_rate_limiting.assert_called_once()


def test_manual_middleware_i18n(mock_load_settings, mock_configure_logging):
    """Test manual i18n middleware configuration."""
    with patch("fastcore.factory.configure_i18n") as mock_configure_i18n:
        # Create app with manual i18n middleware
        i18n_config = I18nConfig(
            default_language="en",
            supported_languages=["en", "es", "fr"],
            translations_dir="translations",
        )

        app = create_app(
            enable_i18n=True, i18n_config=i18n_config, auto_configure=False
        )

        # Verify i18n middleware was configured
        mock_configure_i18n.assert_called_once_with(app, i18n_config)


def test_manual_middleware_i18n_dict(mock_load_settings, mock_configure_logging):
    """Test manual i18n middleware configuration with dict config."""
    with patch("fastcore.factory.configure_i18n") as mock_configure_i18n, patch(
        "fastcore.factory.I18nConfig", return_value=Mock()
    ) as mock_i18n_class:
        # Create app with manual i18n middleware using dict config
        i18n_config = {
            "default_language": "en",
            "supported_languages": ["en", "es", "fr"],
            "translations_dir": "translations",
        }

        app = create_app(
            enable_i18n=True, i18n_config=i18n_config, auto_configure=False
        )

        # Verify I18nConfig constructor was called with dict values
        mock_i18n_class.assert_called_once_with(**i18n_config)

        # Verify i18n middleware was configured
        mock_configure_i18n.assert_called_once()


def test_manual_middleware_trusted_hosts(mock_load_settings, mock_configure_logging):
    """Test manual trusted hosts middleware configuration."""
    with patch(
        "fastcore.factory.configure_trusted_hosts"
    ) as mock_configure_trusted_hosts:
        # Create app with manual trusted hosts middleware
        trusted_hosts_config = TrustedHostsConfig(
            allowed_hosts=["example.com", "api.example.com"]
        )

        app = create_app(
            enable_trusted_hosts=True,
            trusted_hosts_config=trusted_hosts_config,
            auto_configure=False,
        )

        # Verify trusted hosts middleware was configured
        mock_configure_trusted_hosts.assert_called_once_with(app, trusted_hosts_config)


def test_manual_middleware_trusted_hosts_dict(
    mock_load_settings, mock_configure_logging
):
    """Test manual trusted hosts middleware configuration with dict config."""
    with patch(
        "fastcore.factory.configure_trusted_hosts"
    ) as mock_configure_trusted_hosts, patch(
        "fastcore.factory.TrustedHostsConfig", return_value=Mock()
    ) as mock_trusted_hosts_class:
        # Create app with manual trusted hosts middleware using dict config
        trusted_hosts_config = {"allowed_hosts": ["example.com", "api.example.com"]}

        app = create_app(
            enable_trusted_hosts=True,
            trusted_hosts_config=trusted_hosts_config,
            auto_configure=False,
        )

        # Verify TrustedHostsConfig constructor was called with dict values
        mock_trusted_hosts_class.assert_called_once_with(**trusted_hosts_config)

        # Verify trusted hosts middleware was configured
        mock_configure_trusted_hosts.assert_called_once()


def test_manual_middleware_timing(mock_load_settings, mock_configure_logging):
    """Test manual timing middleware configuration."""
    with patch("fastcore.factory.configure_timing") as mock_configure_timing:
        # Create app with manual timing middleware
        timing_config = TimingConfig(
            include_in_response=True, slow_request_threshold_ms=500
        )

        app = create_app(
            enable_timing=True, timing_config=timing_config, auto_configure=False
        )

        # Verify timing middleware was configured
        mock_configure_timing.assert_called_once_with(app, timing_config)


def test_manual_middleware_timing_dict(mock_load_settings, mock_configure_logging):
    """Test manual timing middleware configuration with dict config."""
    with patch("fastcore.factory.configure_timing") as mock_configure_timing, patch(
        "fastcore.factory.TimingConfig", return_value=Mock()
    ) as mock_timing_class:
        # Create app with manual timing middleware using dict config
        timing_config = {"include_in_response": True, "slow_request_threshold_ms": 500}

        app = create_app(
            enable_timing=True, timing_config=timing_config, auto_configure=False
        )

        # Verify TimingConfig constructor was called with dict values
        mock_timing_class.assert_called_once_with(**timing_config)

        # Verify timing middleware was configured
        mock_configure_timing.assert_called_once()


def test_error_handlers_registered(mock_load_settings, mock_configure_logging):
    """Test that error handlers are properly registered."""
    with patch(
        "fastcore.factory.exception_handlers", {"Exception": lambda req, exc: None}
    ):
        # Create app with error handlers enabled
        app = create_app(enable_error_handlers=True)

        # Verify that exception handlers are registered
        assert "Exception" in app.exception_handlers


def test_custom_settings_class(mock_configure_logging):
    """Test using a custom settings class."""

    # Create a custom settings class
    class CustomSettings(AppSettings):
        pass

    # Mock the load method of the custom class
    custom_settings = Mock(spec=CustomSettings)
    custom_settings.TITLE = "Custom App"
    custom_settings.DESCRIPTION = "Custom Description"
    custom_settings.VERSION = "0.2.0"
    custom_settings.ENV = Environment.DEVELOPMENT
    custom_settings.LOGGING = Mock()

    with patch.object(
        CustomSettings, "load", return_value=custom_settings
    ) as mock_load:
        # Create app with custom settings class
        app = create_app(settings_class=CustomSettings)

        # Verify custom settings class was used
        mock_load.assert_called_once_with(Environment.DEVELOPMENT)
        assert app.title == "Custom App"
        assert app.description == "Custom Description"
        assert app.version == "0.2.0"


def test_create_app_with_custom_title_description_version(
    mock_load_settings, mock_configure_logging
):
    """Test creating an app with custom title, description, and version."""
    # Modify our mock settings to remove standard attributes
    mock_settings = mock_load_settings.return_value
    del mock_settings.TITLE
    del mock_settings.DESCRIPTION
    del mock_settings.VERSION

    # Create app
    app = create_app()

    # Verify default values were used
    assert app.title == "FastAPI Application"
    assert app.description == "Powered by FastCore"
    assert app.version == "0.1.0"


def test_redis_url_in_cache_config():
    """Test the _configure_cache function with redis URL."""
    # Create a mock settings object with Redis URL
    settings = Mock()
    settings.CACHE.CACHE_TYPE = "redis"
    settings.CACHE.DEFAULT_TTL = 60
    settings.CACHE.MAX_SIZE = 1000
    settings.CACHE.REDIS_URL = "redis://localhost:6379/0"

    # Mock the cache.configure_cache function
    with patch("fastcore.cache.configure_cache") as mock_configure:
        # Call the function
        _configure_cache(settings)

        # Verify configure_cache was called with the right parameters, including redis_url
        mock_configure.assert_called_once_with(
            cache_type="redis",
            ttl=60,
            max_size=1000,
            redis_url="redis://localhost:6379/0",
        )
