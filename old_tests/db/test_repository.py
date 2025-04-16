"""
Tests for the repository pattern implementation.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from fastcore.db.repository import BaseRepository
from fastcore.db.session import Base


# Define test models
class UserModel(Base):
    """Test SQLAlchemy model for users."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    is_active = Column(Integer, default=1)


class UserCreate(BaseModel):
    """Test Pydantic schema for user creation."""

    email: str
    name: str


class UserUpdate(BaseModel):
    """Test Pydantic schema for user updates."""

    name: str | None = None
    is_active: bool | None = None


class TestBaseRepository:
    """Test cases for the BaseRepository class."""

    def setup_method(self):
        """Set up test environment."""
        self.db = MagicMock()
        self.user_repo = BaseRepository[UserModel, UserCreate, UserUpdate](UserModel)

    def test_get(self):
        """Test get method."""
        # Setup mock return value
        mock_user = UserModel(id=1, email="test@example.com", name="Test User")
        self.db.get.return_value = mock_user

        # Call method
        result = self.user_repo.get(self.db, 1)

        # Verify results
        self.db.get.assert_called_once_with(UserModel, 1)
        assert result == mock_user

    def test_get_or_404_found(self):
        """Test get_or_404 when object exists."""
        # Setup mock
        mock_user = UserModel(id=1, email="test@example.com", name="Test User")
        self.db.get.return_value = mock_user

        # Call method
        result = self.user_repo.get_or_404(self.db, 1)

        # Verify results
        assert result == mock_user

    def test_get_or_404_not_found(self):
        """Test get_or_404 when object doesn't exist."""
        # Setup mock to return None (not found)
        self.db.get.return_value = None

        # Call method and expect exception
        with pytest.raises(HTTPException) as excinfo:
            self.user_repo.get_or_404(self.db, 999)

        # Verify exception details
        assert excinfo.value.status_code == 404
        assert "UserModel with id 999 not found" in excinfo.value.detail

    def test_get_multi(self):
        """Test get_multi method."""
        # Setup mock
        mock_users = [
            UserModel(id=1, email="user1@example.com", name="User 1"),
            UserModel(id=2, email="user2@example.com", name="User 2"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        self.db.execute.return_value = mock_result

        # Call method
        result = self.user_repo.get_multi(self.db, skip=0, limit=10, is_active=1)

        # Verify results
        assert self.db.execute.called
        assert result == mock_users

    def test_create_from_dict(self):
        """Test create method with dict input."""
        # Setup test data and mocks
        user_data = {"email": "new@example.com", "name": "New User"}

        # Call method
        result = self.user_repo.create(self.db, obj_in=user_data)

        # Verify database operations were called
        assert self.db.add.called
        assert self.db.commit.called
        assert self.db.refresh.called

    def test_create_from_model(self):
        """Test create method with Pydantic model input."""
        # Setup test data and mocks
        user_data = UserCreate(email="new@example.com", name="New User")

        # Call method
        result = self.user_repo.create(self.db, obj_in=user_data)

        # Verify database operations were called
        assert self.db.add.called
        assert self.db.commit.called
        assert self.db.refresh.called

    def test_create_integrity_error(self):
        """Test create method handles IntegrityError."""
        # Setup test data and make db.commit raise IntegrityError
        user_data = {"email": "duplicate@example.com", "name": "Duplicate User"}
        self.db.commit.side_effect = IntegrityError("statement", "params", "orig")

        # Call method and expect exception
        with pytest.raises(HTTPException) as excinfo:
            self.user_repo.create(self.db, obj_in=user_data)

        # Verify exception details and rollback was called
        assert excinfo.value.status_code == 400
        assert "Database integrity error" in excinfo.value.detail
        assert self.db.rollback.called

    def test_update(self):
        """Test update method."""
        # Setup test data and mocks
        user = UserModel(id=1, email="user@example.com", name="User")
        update_data = {"name": "Updated User", "is_active": False}

        # Call method
        result = self.user_repo.update(self.db, obj=user, obj_in=update_data)

        # Verify object was updated correctly
        assert user.name == "Updated User"
        assert user.is_active == False
        assert self.db.add.called
        assert self.db.commit.called
        assert self.db.refresh.called

    def test_update_pydantic_model(self):
        """Test update method with Pydantic model input."""
        # Setup test data and mocks
        user = UserModel(id=1, email="user@example.com", name="User", is_active=1)
        update_data = UserUpdate(name="Updated Via Pydantic", is_active=False)

        # Call method
        result = self.user_repo.update(self.db, obj=user, obj_in=update_data)

        # Verify object was updated correctly
        assert user.name == "Updated Via Pydantic"
        assert user.is_active == False
        assert self.db.add.called
        assert self.db.commit.called
        assert self.db.refresh.called

    def test_delete(self):
        """Test delete method."""
        # Setup mock user to return from get_or_404
        mock_user = UserModel(id=1, email="delete@example.com", name="Delete Me")

        # Mock the get_or_404 method to return our mock user
        with patch.object(BaseRepository, "get_or_404", return_value=mock_user):
            # Call method
            result = self.user_repo.delete(self.db, id=1)

            # Verify database operations
            self.db.delete.assert_called_with(mock_user)
            assert self.db.commit.called
            assert result == mock_user

    def test_exists_true(self):
        """Test exists method when record exists."""
        # Setup mock to return a result
        mock_result = MagicMock()
        mock_result.first.return_value = ("something",)
        self.db.execute.return_value = mock_result

        # Call method
        result = self.user_repo.exists(self.db, email="exists@example.com")

        # Verify result
        assert result is True
        assert self.db.execute.called

    def test_exists_false(self):
        """Test exists method when record doesn't exist."""
        # Setup mock to return no result
        mock_result = MagicMock()
        mock_result.first.return_value = None
        self.db.execute.return_value = mock_result

        # Call method
        result = self.user_repo.exists(self.db, email="nonexistent@example.com")

        # Verify result
        assert result is False
        assert self.db.execute.called
