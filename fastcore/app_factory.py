"""
Application factory for FastAPI applications.

This module provides functions to create and configure FastAPI applications
with sensible defaults, making it easy to bootstrap new projects.
"""

from typing import Any, Callable, Dict, List, Optional, Type

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

# Logger for this module
logger = get_logger(__name__)


def create_app(
    env: Environment = Environment.DEVELOPMENT,
    settings_class: Type[AppSettings] = AppSettings,
    enable_cors: bool = True,
    enable_error_handlers: bool = True,
    enable_database: bool = False,
    enable_logging: bool = True,
    cors_origins: List[str] = None,
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
        cors_origins: List of allowed CORS origins (defaults to ["*"] in development)
        middlewares: Additional middlewares to add
        exception_handler_overrides: Custom exception handlers to override defaults
        db_echo: Whether to echo SQL statements (only used when enable_database is True)

    Returns:
        Configured FastAPI application

    Example:
        ```python
        from fastcore.app_factory import create_app
        from fastcore.config.base import Environment

        app = create_app(env=Environment.DEVELOPMENT, enable_database=True)

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

    # Create FastAPI app with settings
    app = FastAPI(
        title=getattr(settings, "TITLE", "FastAPI Application"),
        description=getattr(settings, "DESCRIPTION", "Powered by FastCore"),
        version=getattr(settings, "VERSION", "0.1.0"),
    )

    # Register settings
    app.state.settings = settings

    # Add CORS middleware
    if enable_cors:
        default_origins = ["*"] if env == Environment.DEVELOPMENT else []
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins or default_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.debug(
            f"CORS middleware configured with origins: {cors_origins or default_origins}"
        )

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

    # Initialize database if enabled
    if enable_database:
        # Set up database startup/shutdown events
        @app.on_event("startup")
        def startup_db_client():
            logger.info("Initializing database connection")
            initialize_db(
                settings=settings.DB if hasattr(settings, "DB") else None, echo=db_echo
            )
            logger.info("Database connection initialized successfully")

    # Configure cache on startup
    configure_cache_on_startup(app, settings)

    # Add health check endpoint
    @app.get("/health", tags=["system"])
    def health_check():
        logger.debug("Health check endpoint called")
        return {"status": "ok", "environment": env}

    # Log application startup
    logger.info(f"FastAPI application '{app.title}' configured successfully")

    return app


def configure_cache_on_startup(app: FastAPI, settings: AppSettings) -> None:
    """
    Configure the cache system on application startup.

    Args:
        app: The FastAPI application
        settings: The application settings
    """

    @app.on_event("startup")
    def setup_cache() -> None:
        """Initialize the cache when the application starts."""
        cache_config = settings.CACHE

        if cache_config.CACHE_TYPE == "redis":
            # Configure Redis cache
            configure_cache(
                backend_type="redis",
                host=cache_config.REDIS_HOST,
                port=cache_config.REDIS_PORT,
                db=cache_config.REDIS_DB,
                password=cache_config.REDIS_PASSWORD,
                prefix=cache_config.REDIS_PREFIX,
            )
        elif cache_config.CACHE_TYPE == "memory":
            # Configure memory cache
            configure_cache(
                backend_type="memory",
                max_size=cache_config.MEMORY_CACHE_MAX_SIZE,
            )
        elif cache_config.CACHE_TYPE == "null":
            # Configure null cache (no-op)
            configure_cache(backend_type="null")
        else:
            # Use memory cache as fallback
            configure_cache(backend_type="memory")
