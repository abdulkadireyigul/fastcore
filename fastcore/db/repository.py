"""
Repository pattern implementation for database operations.

This module provides a base repository class that implements standard
CRUD operations for SQLAlchemy models. The repository pattern abstracts
the data access layer from the rest of the application.
"""

from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from fastcore.db.session import Base

# Type variables for models
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository for database operations.

    This class implements standard CRUD operations for a SQLAlchemy model.
    It should be subclassed for each model with specific model types.

    Type Parameters:
        ModelType: The SQLAlchemy model type
        CreateSchemaType: The Pydantic model type for create operations
        UpdateSchemaType: The Pydantic model type for update operations

    Attributes:
        model: The SQLAlchemy model class
    """

    def __init__(self, model: Type[ModelType]):
        """
        Initialize repository with model class.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Get a model instance by ID.

        Args:
            db: Database session
            id: Primary key value

        Returns:
            Model instance or None if not found

        Example:
            ```python
            user_repo = UserRepository(User)
            user = user_repo.get(db, 123)
            ```
        """
        return db.get(self.model, id)

    def get_or_404(self, db: Session, id: Any) -> ModelType:
        """
        Get a model instance by ID or raise 404 exception.

        Args:
            db: Database session
            id: Primary key value

        Returns:
            Model instance

        Raises:
            HTTPException: 404 error if not found

        Example:
            ```python
            user_repo = UserRepository(User)
            user = user_repo.get_or_404(db, 123)
            ```
        """
        obj = self.get(db, id)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} with id {id} not found",
            )
        return obj

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, **filters: Any
    ) -> List[ModelType]:
        """
        Get multiple model instances with pagination.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Optional filter criteria

        Returns:
            List of model instances

        Example:
            ```python
            user_repo = UserRepository(User)
            active_users = user_repo.get_multi(db, skip=0, limit=10, is_active=True)
            ```
        """
        query = select(self.model)

        # Apply filters if provided
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)

        result = db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    def count(self, db: Session, **filters: Any) -> int:
        """
        Count total records matching filters.

        Args:
            db: Database session
            **filters: Optional filter criteria

        Returns:
            Total count

        Example:
            ```python
            user_repo = UserRepository(User)
            total_active = user_repo.count(db, is_active=True)
            ```
        """
        query = select(func.count()).select_from(self.model)

        # Apply filters if provided
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)

        result = db.execute(query).scalar_one()
        return result if result is not None else 0

    def create(
        self, db: Session, *, obj_in: Union[CreateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Create a new model instance.

        Args:
            db: Database session
            obj_in: Data to create instance with

        Returns:
            Created model instance

        Raises:
            HTTPException: 400 error on integrity violation

        Example:
            ```python
            user_repo = UserRepository(User)
            new_user = user_repo.create(db, obj_in=UserCreate(email="user@example.com"))
            ```
        """
        try:
            # Convert pydantic model to dict if needed
            if isinstance(obj_in, BaseModel):
                # Handle both Pydantic V1 and V2
                if hasattr(obj_in, "model_dump"):
                    obj_in_data = obj_in.model_dump()
                else:
                    obj_in_data = obj_in.dict()
            else:
                obj_in_data = obj_in

            # Create model instance
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database integrity error: {str(e)}",
            )
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )

    def update(
        self,
        db: Session,
        *,
        obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """
        Update a model instance.

        Args:
            db: Database session
            obj: Model instance to update
            obj_in: Data to update with

        Returns:
            Updated model instance

        Raises:
            HTTPException: 400 error on integrity violation

        Example:
            ```python
            user_repo = UserRepository(User)
            user = user_repo.get(db, 123)
            updated_user = user_repo.update(db, obj=user, obj_in={"is_active": False})
            ```
        """
        try:
            # Convert pydantic model to dict if needed
            if isinstance(obj_in, BaseModel):
                # Handle both Pydantic V1 and V2
                if hasattr(obj_in, "model_dump"):
                    obj_in_data = obj_in.model_dump(exclude_unset=True)
                else:
                    obj_in_data = obj_in.dict(exclude_unset=True)
            else:
                obj_in_data = obj_in

            # Update attributes
            for field in obj_in_data:
                if hasattr(obj, field):
                    setattr(obj, field, obj_in_data[field])

            db.add(obj)
            db.commit()
            db.refresh(obj)
            return obj
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database integrity error: {str(e)}",
            )
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )

    def delete(self, db: Session, *, id: Any) -> ModelType:
        """
        Delete a model instance.

        Args:
            db: Database session
            id: Primary key value

        Returns:
            Deleted model instance

        Raises:
            HTTPException: 404 error if not found

        Example:
            ```python
            user_repo = UserRepository(User)
            deleted_user = user_repo.delete(db, id=123)
            ```
        """
        obj = self.get_or_404(db, id)
        db.delete(obj)
        db.commit()
        return obj

    def exists(self, db: Session, **filters: Any) -> bool:
        """
        Check if a record matching filters exists.

        Args:
            db: Database session
            **filters: Filter criteria

        Returns:
            True if exists, False otherwise

        Example:
            ```python
            user_repo = UserRepository(User)
            has_admin = user_repo.exists(db, role="admin")
            ```
        """
        query = select(self.model)

        # Apply filters
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)

        return db.execute(query.limit(1)).first() is not None
