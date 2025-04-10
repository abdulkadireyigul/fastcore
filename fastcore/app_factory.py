"""
Application factory for FastAPI applications.

This module provides functions to create and configure FastAPI applications
with sensible defaults, making it easy to bootstrap new projects.
"""

from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, Type, Union

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fastcore.cache.manager import configure_cache
from fastcore.config.app import AppSettings
from fastcore.config.base import Environment
from fastcore.db.session import initialize_db
from fastcore.errors.exceptions import AppError
from fastcore.errors.handlers import exception_handlers
from fastcore.logging import configure_logging, get_logger
from fastcore.middleware import (
    CORSConfig,
    I18nConfig,
    RateLimitConfig,
    TimingConfig,
    TrustedHostsConfig,
    configure_cors,
    configure_i18n,
    configure_rate_limiting,
    configure_timing,
    configure_trusted_hosts,
)

# Logger for this module
logger = get_logger(__name__)


def create_app(
    env: Environment = Environment.DEVELOPMENT,
    settings_class: Type[AppSettings] = AppSettings,
    enable_cors: bool = True,
    enable_error_handlers: bool = True,
    enable_database: bool = False,
    enable_logging: bool = True,
    enable_rate_limiting: bool = False,
    enable_i18n: bool = False,
    enable_trusted_hosts: bool = False,
    enable_timing: bool = False,
    enable_monitoring: bool = False,
    cors_config: Optional[Union[CORSConfig, Dict[str, Any]]] = None,
    rate_limit_config: Optional[Union[RateLimitConfig, Dict[str, Any]]] = None,
    i18n_config: Optional[Union[I18nConfig, Dict[str, Any]]] = None,
    trusted_hosts_config: Optional[Union[TrustedHostsConfig, Dict[str, Any]]] = None,
    timing_config: Optional[Union[TimingConfig, Dict[str, Any]]] = None,
    middlewares: List[Dict[str, Any]] = None,
    exception_handler_overrides: Dict[Type[Exception], Callable] = None,
    db_echo: bool = False,
) -> FastAPI:
    """
    Create and configure a FastAPI application with sensible defaults.

    This factory function creates a FastAPI application with configuration loaded
    from the specified environment, and sets up common middleware and exception handlers.

    Args:
        env: Environment to load configuration for
        settings_class: Settings class to use for configuration
        enable_cors: Whether to enable CORS middleware
        enable_error_handlers: Whether to register default exception handlers
        enable_database: Whether to initialize database connection
        enable_logging: Whether to configure logging based on settings
        enable_rate_limiting: Whether to enable rate limiting middleware
        enable_i18n: Whether to enable internationalization middleware
        enable_trusted_hosts: Whether to enable trusted hosts middleware
        enable_timing: Whether to enable request timing middleware
        enable_monitoring: Whether to enable monitoring features
        cors_config: Configuration for CORS middleware
        rate_limit_config: Configuration for rate limiting middleware
        i18n_config: Configuration for internationalization middleware
        trusted_hosts_config: Configuration for trusted hosts middleware
        timing_config: Configuration for timing middleware
        middlewares: Additional middlewares to add
        exception_handler_overrides: Custom exception handlers to override defaults
        db_echo: Whether to echo SQL statements (only used when enable_database is True)

    Returns:
        Configured FastAPI application

    Example:
        ```python
        from fastcore.app_factory import create_app
        from fastcore.config.base import Environment
        from fastcore.middleware import RateLimitConfig

        # Create app with default settings
        app = create_app(env=Environment.DEVELOPMENT, enable_database=True)

        # Or with custom middleware configuration
        app = create_app(
            env=Environment.PRODUCTION,
            enable_rate_limiting=True,
            rate_limit_config=RateLimitConfig(
                limit=100,
                window_seconds=60,
                exclude_paths=["/docs", "/redoc"]
            )
        )

        @app.get("/")
        def read_root():
            return {"Hello": "World"}
        ```
    """
    # Load settings
    settings = settings_class.load(env)

    # Configure logging if enabled
    if enable_logging:
        configure_logging(
            settings=settings.LOGGING if hasattr(settings, "LOGGING") else None
        )
        logger.info(f"Application starting in {env} environment")

    # Create lifespan context manager for startup and shutdown events
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # --- STARTUP EVENTS ---
        # Initialize database if enabled
        if enable_database:
            logger.info("Initializing database connection")
            initialize_db(
                settings=settings.DB if hasattr(settings, "DB") else None, echo=db_echo
            )
            logger.info("Database connection initialized successfully")

        # Configure cache
        _configure_cache(settings)

        # Yield control to FastAPI
        yield

        # --- SHUTDOWN EVENTS ---
        # Add any cleanup code here if needed
        logger.info("Application shutting down")

    # Create FastAPI app with settings and lifespan
    app = FastAPI(
        title=getattr(settings, "TITLE", "FastAPI Application"),
        description=getattr(settings, "DESCRIPTION", "Powered by FastCore"),
        version=getattr(settings, "VERSION", "0.1.0"),
        lifespan=lifespan,
    )

    # Register settings
    app.state.settings = settings

    # Configure middleware (order is important)

    # 1. Trusted Hosts middleware should be first (validates incoming hosts)
    if enable_trusted_hosts:
        if isinstance(trusted_hosts_config, dict):
            trusted_hosts_config = TrustedHostsConfig(**trusted_hosts_config)
        configure_trusted_hosts(app, trusted_hosts_config)
        logger.debug("Trusted hosts middleware configured")

    # 2. CORS middleware comes next
    if enable_cors:
        if cors_config:
            # Use provided config
            if isinstance(cors_config, dict):
                cors_config = CORSConfig(**cors_config)
            configure_cors(app, cors_config)
        else:
            # Use default CORS configuration based on environment
            default_origins = ["*"] if env == Environment.DEVELOPMENT else []
            configure_cors(app, allow_origins=default_origins)
        logger.debug("CORS middleware configured")

    # 3. Rate limiting middleware
    if enable_rate_limiting:
        if isinstance(rate_limit_config, dict):
            rate_limit_config = RateLimitConfig(**rate_limit_config)
        configure_rate_limiting(app, rate_limit_config)
        logger.debug("Rate limiting middleware configured")

    # 4. i18n middleware
    if enable_i18n:
        if isinstance(i18n_config, dict):
            i18n_config = I18nConfig(**i18n_config)
        configure_i18n(app, i18n_config)
        logger.debug("Internationalization middleware configured")

    # 5. Timing middleware
    if enable_timing:
        if isinstance(timing_config, dict):
            timing_config = TimingConfig(**timing_config)
        configure_timing(app, timing_config)
        logger.debug("Request timing middleware configured")

    # Add custom middlewares
    if middlewares:
        for middleware in middlewares:
            middleware_class = middleware.get("class")
            middleware_args = middleware.get("args", {})
            app.add_middleware(middleware_class, **middleware_args)
            logger.debug(f"Added middleware: {middleware_class.__name__}")

    # Add exception handlers
    if enable_error_handlers:
        # Default handlers
        for exc, handler in exception_handlers.items():
            app.add_exception_handler(exc, handler)

        # Custom handler overrides
        if exception_handler_overrides:
            for exc, handler in exception_handler_overrides.items():
                app.add_exception_handler(exc, handler)

        logger.debug("Exception handlers registered")

    # Add monitoring if enabled
    if enable_monitoring:
        from fastcore.monitoring.instrumentation import instrument_app

        instrument_app(app)
        logger.debug("Monitoring instrumentation enabled")
    else:
        # Add health check endpoint even if full monitoring is disabled
        @app.get("/health", tags=["system"])
        def health_check():
            logger.debug("Health check endpoint called")
            return {"status": "ok", "environment": env}

    # Log application startup
    logger.info(f"FastAPI application '{app.title}' configured successfully")

    return app


def _configure_cache(settings: AppSettings) -> None:
    """Configure cache from settings."""
    if hasattr(settings, "CACHE"):
        try:
            from fastcore.cache import configure_cache

            cache_config = settings.CACHE
            configure_cache(
                cache_type=cache_config.CACHE_TYPE,
                ttl=cache_config.DEFAULT_TTL,
                max_size=cache_config.MAX_SIZE,
                redis_url=cache_config.REDIS_URL
                if hasattr(cache_config, "REDIS_URL")
                else None,
            )
            logger.info(f"Cache configured with backend: {cache_config.CACHE_TYPE}")
        except Exception as e:
            logger.error(f"Failed to configure cache: {str(e)}")
    else:
        logger.debug("No cache configuration found in settings")
