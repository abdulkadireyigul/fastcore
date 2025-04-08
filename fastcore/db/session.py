"""
Database session management for FastAPI applications.

This module provides utilities for creating database sessions,
managing connections, and configuring the database engine.
It self-configures based on the application environment settings.
"""

import os
from typing import Any, Callable, Generator, Optional, TypeVar, cast

from fastapi import Depends
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import sessionmaker, declarative_base

from fastcore.config.app import AppSettings, DatabaseSettings, Environment

# Type alias for SQLAlchemy Session
Session = SQLAlchemySession

# Create a declarative base for SQLAlchemy models
Base = declarative_base()

# Define a type variable for the database dependency
T = TypeVar("T")

# Global database configuration - initialized automatically
_settings: Optional[AppSettings] = None
engine: Optional[Engine] = None
SessionLocal: Optional[Callable[[], Session]] = None


def _get_settings() -> AppSettings:
    """
    Get or initialize application settings.
    
    This internal function ensures settings are loaded from the environment
    using the application's environment configuration.
    
    Returns:
        Application settings based on the current environment
    """
    global _settings
    
    if _settings is None:
        # Try to detect environment or default to development
        env_name = os.environ.get("APP_ENVIRONMENT", "development")
        try:
            env = Environment(env_name.lower())
        except ValueError:
            env = Environment.DEVELOPMENT
        
        _settings = AppSettings.load(env)
    
    return _settings


class DatabaseManager:
    """
    Database connection manager.

    This class handles the creation and configuration of the database engine
    and session factory.

    Attributes:
        settings: Database connection settings
        engine: SQLAlchemy engine instance
        session_factory: Factory function for creating new database sessions
    """

    def __init__(
        self, settings: DatabaseSettings, echo: bool = False, pool_pre_ping: bool = True
    ) -> None:
        """
        Initialize database manager with connection settings.

        Args:
            settings: Database connection settings
            echo: Whether to echo SQL statements (useful for debugging)
            pool_pre_ping: Whether to enable connection pool pre-ping
        """
        self.settings = settings
        self.engine = self._create_engine(echo, pool_pre_ping)
        self.session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def _create_engine(self, echo: bool = False, pool_pre_ping: bool = True) -> Engine:
        """
        Create a SQLAlchemy engine instance.
        
        Args:
            echo: Whether to echo SQL statements
            pool_pre_ping: Whether to enable connection pool pre-ping
            
        Returns:
            Configured SQLAlchemy engine
        """
        url = self.settings.URL
        
        # Basic connection arguments
        engine_args = {
            "echo": echo,
            "pool_pre_ping": pool_pre_ping,
        }
        
        # SQLite has different connection pooling requirements
        if url.startswith('sqlite'):
            return create_engine(url, **engine_args)
        
        # For other database systems, add more connection pool settings
        engine_args.update({
            "pool_size": self.settings.POOL_SIZE,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        })
        
        return create_engine(url, **engine_args)

    def get_session(self) -> Generator[Session, None, None]:
        """
        Create a new database session.

        Yields:
            A SQLAlchemy session that will be automatically closed
        """
        session: Session = self.session_factory()
        try:
            yield session
        finally:
            session.close()


def initialize_db(settings: Optional[DatabaseSettings] = None, echo: bool = False) -> None:
    """
    Initialize the database connection.
    
    This function can be called during application startup to configure
    the database connection. If settings are not provided, it will use
    the settings from the application environment configuration.
    
    Args:
        settings: Database connection settings (optional)
        echo: Whether to echo SQL statements (useful for debugging)
    
    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.db import initialize_db
        
        app = FastAPI()
        
        @app.on_event("startup")
        def startup_db_client():
            # Automatically uses settings from environment
            initialize_db()
        
        # Or with custom settings:
        # initialize_db(custom_settings)
        ```
    """
    global engine, SessionLocal
    
    # If settings are not provided, use the app settings from environment
    if settings is None:
        app_settings = _get_settings()
        
        # Check if database settings exist in app settings
        if app_settings.DB is None:
            raise RuntimeError(
                "Database settings not found in application configuration. "
                "Please provide database settings explicitly or set them in environment variables."
            )
        
        settings = app_settings.DB
    
    db_manager = DatabaseManager(settings, echo=echo)
    engine = db_manager.engine
    SessionLocal = db_manager.session_factory


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session injection.
    
    This function will automatically initialize the database connection
    if it hasn't been initialized yet.
    
    Yields:
        A SQLAlchemy session that will be automatically closed

    Raises:
        RuntimeError: If the database has not been initialized

    Example:
        ```python
        from fastapi import Depends, FastAPI
        from fastcore.db.session import get_db, Session

        app = FastAPI()

        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            # Use the database session
            return db.query(Item).all()
        ```
    """
    global SessionLocal
    
    # Auto-initialize if not already initialized
    if SessionLocal is None:
        initialize_db()
        
        # If still None after initialization, raise an error
        if SessionLocal is None:
            raise RuntimeError(
                "Database initialization failed. Please check your database configuration."
            )
    
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def db_dependency(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to inject a database session as the first parameter.
    
    This function will automatically initialize the database connection
    if it hasn't been initialized yet.
    
    Args:
        func: Function that takes a database session as its first parameter

    Returns:
        Decorated function that will receive an active database session

    Example:
        ```python
        @db_dependency
        def get_user_by_email(db: Session, email: str) -> Optional[User]:
            return db.query(User).filter(User.email == email).first()
        ```
    """
    def wrapper(*args: Any, **kwargs: Any) -> T:
        global SessionLocal
        
        # Auto-initialize if not already initialized
        if SessionLocal is None:
            initialize_db()
            
            # If still None after initialization, raise an error
            if SessionLocal is None:
                raise RuntimeError(
                    "Database initialization failed. Please check your database configuration."
                )
        
        with SessionLocal() as session:
            return func(session, *args, **kwargs)
    
    return cast(Callable[..., T], wrapper)
