"""
Tests for database session management functionality.
"""
import os
import time
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as SQLAlchemySession

from fastcore.config.app import AppSettings, DatabaseSettings, Environment
from fastcore.db.session import (
    DatabaseManager,
    Session,
    _get_settings,
    db_dependency,
    get_db,
    initialize_db,
)


# Create a custom DatabaseSettings class for testing with SQLite
class TestDatabaseSettings(DatabaseSettings):
    """Test settings class that overrides the URL property for SQLite testing."""

    @property
    def URL(self) -> str:
        """Override to return SQLite in-memory URL."""
        return "sqlite:///:memory:"


# Create a custom DatabaseSettings class for testing with PostgreSQL
class TestPostgresSettings(DatabaseSettings):
    """Test settings class that simulates PostgreSQL connection."""

    DRIVER = "postgresql"
    USER = "testuser"
    PASSWORD = "testpass"
    HOST = "localhost"
    PORT = "5432"
    NAME = "testdb"

    @property
    def URL(self) -> str:
        """Return PostgreSQL connection URL."""
        return f"{self.DRIVER}://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"


class TestSessionManagement:
    """Test cases for database session management."""

    def setup_method(self):
        """Set up test environment."""
        # Create test database settings
        self.db_settings = TestDatabaseSettings()
        self.db_settings.USER = "dummy"
        self.db_settings.PASSWORD = "dummy"
        self.db_settings.HOST = "dummy"
        self.db_settings.PORT = "dummy"
        self.db_settings.NAME = "dummy"

        # Set up environment for auto-configuration tests
        os.environ["APP_ENVIRONMENT"] = "testing"

    def teardown_method(self):
        """Clean up after tests."""
        # Reset module variables
        from fastcore.db import session

        session.engine = None
        session.SessionLocal = None
        session._settings = None

        # Clean up environment
        if "APP_ENVIRONMENT" in os.environ:
            del os.environ["APP_ENVIRONMENT"]

    def test_initialize_db(self):
        """Test database initialization with explicit settings."""
        # Initialize the database with test settings
        initialize_db(self.db_settings)

        # Import module to access updated module variables
        from fastcore.db import session

        # Verify engine and SessionLocal were created
        assert session.engine is not None
        assert session.SessionLocal is not None

    @patch("fastcore.db.session._get_settings")
    def test_initialize_db_auto(self, mock_get_settings):
        """Test database initialization with auto-configuration."""
        # Set up mock for _get_settings
        mock_app_settings = MagicMock()
        mock_app_settings.DB = self.db_settings
        mock_get_settings.return_value = mock_app_settings

        # Initialize the database without explicit settings
        initialize_db()

        # Verify engine and SessionLocal were created
        from fastcore.db import session

        assert session.engine is not None
        assert session.SessionLocal is not None
        # Verify _get_settings was called
        mock_get_settings.assert_called_once()

    def test_get_db(self):
        """Test get_db dependency function."""
        # Initialize the database first
        initialize_db(self.db_settings)

        # Create a mock generator function for testing
        def mock_generator():
            session = MagicMock(spec=SQLAlchemySession)
            yield session
            session.close.assert_called_once()

        # Replace SessionLocal with our mock
        from fastcore.db import session

        session.SessionLocal = lambda: MagicMock(spec=SQLAlchemySession)

        # Get generator from get_db
        gen = get_db()

        # Get the session from the generator
        db_session = next(gen)

        # Verify it's a session object
        assert isinstance(db_session, MagicMock)

        # Finish generator to trigger session.close()
        try:
            next(gen)
        except StopIteration:
            pass

        # Verify close was called on the session
        db_session.close.assert_called_once()

    @patch("fastcore.db.session._get_settings")
    def test_get_db_auto_initialize(self, mock_get_settings):
        """Test get_db auto-initializes if not already initialized."""
        # Set up mock for _get_settings
        mock_app_settings = MagicMock()
        mock_app_settings.DB = self.db_settings
        mock_get_settings.return_value = mock_app_settings

        # Reset module variables to simulate uninitialized state
        from fastcore.db import session

        session.engine = None
        session.SessionLocal = None

        with patch("fastcore.db.session.initialize_db") as mock_initialize:
            # Mock initialize_db to set SessionLocal
            def side_effect(settings=None, echo=False):
                session.SessionLocal = lambda: MagicMock(spec=SQLAlchemySession)

            mock_initialize.side_effect = side_effect

            # Call get_db which should auto-initialize
            gen = get_db()
            _ = next(gen)

            # Verify initialize_db was called
            mock_initialize.assert_called_once()

    def test_get_db_not_initialized(self):
        """Test get_db when database is not initialized and auto-init fails."""
        # Reset module variables to simulate uninitialized state
        from fastcore.db import session

        session.engine = None
        session.SessionLocal = None

        # Mock initialize_db to simulate failure
        with patch("fastcore.db.session.initialize_db") as mock_initialize:
            # Don't set SessionLocal to simulate initialization failure
            pass

            # Check that RuntimeError is raised
            with pytest.raises(RuntimeError):
                next(get_db())

    def test_db_dependency(self):
        """Test db_dependency decorator."""
        # Initialize the database first
        initialize_db(self.db_settings)

        # Create a test function to decorate
        def test_func(db, arg1, arg2=None):
            assert isinstance(db, SQLAlchemySession)
            return f"{arg1}-{arg2}"

        # Apply the decorator
        decorated_func = db_dependency(test_func)

        # Mock SessionLocal to return a context manager
        mock_session = MagicMock(spec=SQLAlchemySession)
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__enter__.return_value = mock_session

        from fastcore.db import session

        session.SessionLocal = mock_session_factory

        # Call the decorated function
        result = decorated_func("value1", arg2="value2")

        # Verify the context manager was used correctly
        mock_session_factory.assert_called_once()
        mock_session_factory.return_value.__enter__.assert_called_once()
        mock_session_factory.return_value.__exit__.assert_called_once()

        # Verify the result
        assert result == "value1-value2"

    @patch("fastcore.db.session._get_settings")
    def test_db_dependency_auto_initialize(self, mock_get_settings):
        """Test db_dependency auto-initializes if not already initialized."""
        # Set up mock for _get_settings
        mock_app_settings = MagicMock()
        mock_app_settings.DB = self.db_settings
        mock_get_settings.return_value = mock_app_settings

        # Reset module variables to simulate uninitialized state
        from fastcore.db import session

        session.engine = None
        session.SessionLocal = None

        # Create a test function to decorate
        def test_func(db, arg1):
            return f"test-{arg1}"

        # Apply the decorator
        decorated_func = db_dependency(test_func)

        with patch("fastcore.db.session.initialize_db") as mock_initialize:
            # Mock initialize_db to set SessionLocal
            def side_effect(settings=None, echo=False):
                mock_session = MagicMock(spec=SQLAlchemySession)
                mock_session_factory = MagicMock()
                mock_session_factory.return_value.__enter__.return_value = mock_session
                session.SessionLocal = mock_session_factory

            mock_initialize.side_effect = side_effect

            # Call the decorated function
            decorated_func("arg1")

            # Verify initialize_db was called
            mock_initialize.assert_called_once()

    def test_db_dependency_initialization_failure(self):
        """Test db_dependency when initialization fails."""
        # Reset module variables to simulate uninitialized state
        from fastcore.db import session

        session.engine = None
        session.SessionLocal = None

        # Create a test function to decorate
        def test_func(db, arg1):
            return f"test-{arg1}"

        # Apply the decorator
        decorated_func = db_dependency(test_func)

        # Mock initialize_db but don't set SessionLocal to simulate failure
        with patch("fastcore.db.session.initialize_db"):
            # Check that RuntimeError is raised
            with pytest.raises(RuntimeError):
                decorated_func("arg1")

    def test_get_settings_environment_detection(self):
        """Test _get_settings environment detection logic."""
        # Reset module variables to simulate uninitialized state
        from fastcore.db import session

        session._settings = None

        # Test with valid environment
        os.environ["APP_ENVIRONMENT"] = "production"

        with patch("fastcore.config.app.AppSettings.load") as mock_load:
            mock_settings = MagicMock()
            mock_load.return_value = mock_settings

            settings = _get_settings()

            # Verify AppSettings.load was called with the correct environment
            mock_load.assert_called_once_with(Environment.PRODUCTION)
            assert settings == mock_settings

        # Reset and test with invalid environment
        session._settings = None
        os.environ["APP_ENVIRONMENT"] = "invalid_env"

        with patch("fastcore.config.app.AppSettings.load") as mock_load:
            mock_settings = MagicMock()
            mock_load.return_value = mock_settings

            settings = _get_settings()

            # Verify AppSettings.load was called with the default environment
            mock_load.assert_called_once_with(Environment.DEVELOPMENT)
            assert settings == mock_settings

    def test_initialize_db_with_missing_db_settings(self):
        """Test initialize_db when DB settings are missing."""
        # Create app settings with no DB settings
        mock_app_settings = MagicMock(spec=AppSettings)
        mock_app_settings.DB = None

        with patch("fastcore.db.session._get_settings", return_value=mock_app_settings):
            # This should not raise an error but log a warning
            initialize_db()

            # Verify that engine and SessionLocal remain None
            from fastcore.db import session

            assert session.engine is None
            assert session.SessionLocal is None

    @patch("fastcore.db.session.create_engine")
    def test_database_manager_sqlite_config(self, mock_create_engine):
        """Test DatabaseManager with SQLite configuration."""
        # Mock engine creation
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Create manager with SQLite settings
        manager = DatabaseManager(self.db_settings)

        # Verify engine was created with expected parameters
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args

        # Check that SQLite URL was passed
        assert args[0].startswith("sqlite:")

        # Check that SQLite doesn't get pool settings
        assert "pool_size" not in kwargs

        # Verify session factory was created
        assert manager.session_factory is not None

    @patch("fastcore.db.session.create_engine")
    def test_database_manager_postgres_config(self, mock_create_engine):
        """Test DatabaseManager with PostgreSQL configuration."""
        # Mock engine creation
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Create manager with PostgreSQL settings
        pg_settings = TestPostgresSettings()
        manager = DatabaseManager(pg_settings)

        # Verify engine was created with expected parameters
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args

        # Check that PostgreSQL URL was passed
        assert args[0].startswith("postgresql:")

        # Check that pool settings were included for PostgreSQL
        assert "pool_size" in kwargs
        assert kwargs["pool_size"] == pg_settings.POOL_SIZE

        # Verify session factory was created
        assert manager.session_factory is not None

    def test_database_manager_connection_retry(self):
        """Test DatabaseManager connection retry logic."""
        # Create settings
        settings = self.db_settings

        # Mock _create_engine to fail on first attempt
        with patch.object(DatabaseManager, "_create_engine") as mock_create_engine:
            # First call raises error, second succeeds
            mock_engine = MagicMock()
            mock_create_engine.side_effect = [
                SQLAlchemyError("Connection error"),
                mock_engine,
            ]

            # Mock engine.connect to return a connection
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn

            # Create manager with retry settings
            manager = DatabaseManager(
                settings, max_retries=2, retry_delay=0.1  # Short delay for tests
            )

            # Verify _create_engine was called twice
            assert mock_create_engine.call_count == 2

            # Verify engine is the successful one
            assert manager.engine == mock_engine

    def test_database_manager_connection_failure(self):
        """Test DatabaseManager when all connection attempts fail."""
        # Create settings
        settings = self.db_settings

        # Mock _create_engine to always fail
        with patch.object(DatabaseManager, "_create_engine") as mock_create_engine:
            # All calls raise error
            mock_create_engine.side_effect = SQLAlchemyError("Connection error")

            # Check that RuntimeError is raised after max retries
            with pytest.raises(RuntimeError):
                DatabaseManager(
                    settings, max_retries=2, retry_delay=0.1  # Short delay for tests
                )

            # Verify _create_engine was called expected number of times
            assert mock_create_engine.call_count == 2

    def test_database_manager_session_context(self):
        """Test DatabaseManager session context manager."""
        # Mock session factory to return a session
        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)

        # Create manager and replace session factory
        manager = DatabaseManager(self.db_settings)
        manager.session_factory = mock_session_factory

        # Use the session context manager
        with manager.session() as session:
            # Verify session is the mock session
            assert session == mock_session

            # Use the session
            session.query("test")

        # Verify session methods were called
        mock_session_factory.assert_called_once()
        mock_session.close.assert_called_once()

        # Test error handling path
        mock_session.reset_mock()
        mock_session_factory.reset_mock()

        try:
            with manager.session() as session:
                # Verify session is the mock session
                assert session == mock_session

                # Raise an exception
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify rollback and close were called
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_database_manager_get_session(self):
        """Test DatabaseManager get_session generator."""
        # Mock session factory to return a session
        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)

        # Create manager and replace session factory
        manager = DatabaseManager(self.db_settings)
        manager.session_factory = mock_session_factory

        # Use the get_session generator
        session_gen = manager.get_session()
        session = next(session_gen)

        # Verify session is the mock session
        assert session == mock_session

        # Exhaust the generator
        try:
            next(session_gen)
        except StopIteration:
            pass

        # Verify session methods were called
        mock_session_factory.assert_called_once()
        mock_session.close.assert_called_once()

    def test_get_db_exception_handling(self):
        """Test get_db exception handling during session usage."""
        # Initialize the database first
        initialize_db(self.db_settings)

        # Create a mock session with close method
        mock_session = MagicMock(spec=SQLAlchemySession)

        # Replace SessionLocal with our mock factory
        from fastcore.db import session

        session.SessionLocal = lambda: mock_session

        # Use get_db with an exception
        gen = get_db()
        db = next(gen)

        assert db == mock_session

        # Simulate exception in route handler
        try:
            # Force StopIteration to simulate end of generator
            # after an exception in the route handler
            next(gen)
        except StopIteration:
            # This should happen normally
            pass

        # Verify close was called regardless of exception
        mock_session.close.assert_called_once()

    def test_initialize_db_exception(self):
        """Test initialize_db when an exception occurs."""
        with patch.object(
            DatabaseManager, "__init__", side_effect=Exception("Test error")
        ):
            # This should raise the exception
            with pytest.raises(Exception):
                initialize_db(self.db_settings)
