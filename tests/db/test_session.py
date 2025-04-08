"""
Tests for database session management functionality.
"""
import os
import pytest
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session as SQLAlchemySession

from fastcore.config.app import DatabaseSettings
from fastcore.db.session import initialize_db, get_db, db_dependency, Session, _get_settings


# Create a custom DatabaseSettings class for testing with SQLite
class TestDatabaseSettings(DatabaseSettings):
    """Test settings class that overrides the URL property for SQLite testing."""
    
    @property
    def URL(self) -> str:
        """Override to return SQLite in-memory URL."""
        return "sqlite:///:memory:"


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

    @patch('fastcore.db.session._get_settings')
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

    @patch('fastcore.db.session._get_settings')
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
        
        with patch('fastcore.db.session.initialize_db') as mock_initialize:
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
        with patch('fastcore.db.session.initialize_db') as mock_initialize:
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
        
    @patch('fastcore.db.session._get_settings')
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
        
        with patch('fastcore.db.session.initialize_db') as mock_initialize:
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
