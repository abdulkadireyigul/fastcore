"""
Application factory for FastAPI applications.

This module provides functions to create and configure FastAPI applications
with sensible defaults, making it easy to bootstrap new projects.
"""

from typing import Any, Callable, Dict, List, Optional, Type

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fastcore.config.app import AppSettings
from fastcore.config.base import Environment
from fastcore.db.session import initialize_db
from fastcore.errors.exceptions import AppException
from fastcore.errors.handlers import exception_handlers


def create_app(
    env: Environment = Environment.DEVELOPMENT,
    settings_class: Type[AppSettings] = AppSettings,
    enable_cors: bool = True,
    enable_error_handlers: bool = True,
    enable_database: bool = False,
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
    settings = settings_class.from_env(env)
    
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
    
    # Add custom middlewares
    if middlewares:
        for middleware in middlewares:
            middleware_class = middleware.get("class")
            middleware_args = middleware.get("args", {})
            app.add_middleware(middleware_class, **middleware_args)
    
    # Add exception handlers
    if enable_error_handlers:
        # Default handlers
        for exc, handler in exception_handlers.items():
            app.add_exception_handler(exc, handler)
        
        # Custom handler overrides
        if exception_handler_overrides:
            for exc, handler in exception_handler_overrides.items():
                app.add_exception_handler(exc, handler)
    
    # Initialize database if enabled
    if enable_database:
        # Set up database startup/shutdown events
        @app.on_event("startup")
        def startup_db_client():
            initialize_db(settings=settings.DB if hasattr(settings, "DB") else None, echo=db_echo)
    
    # Add health check endpoint
    @app.get("/health", tags=["system"])
    def health_check():
        return {"status": "ok", "environment": env}

    return app