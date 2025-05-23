from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastcore.errors.exceptions import DBError, NotFoundError
from fastcore.logging.manager import ensure_logger

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing basic async CRUD operations for SQLAlchemy models.

    Only async SQLAlchemy is supported. No sync support or advanced query helpers.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session
        self.logger = ensure_logger(None, self.__class__.__name__)

    async def get_by_id(self, id: Any) -> ModelType:
        """Retrieve a single record by primary key."""
        try:
            instance: Optional[ModelType] = await self.session.get(self.model, id)
            if instance is None:
                raise NotFoundError(resource_type=self.model.__name__, resource_id=id)
            self.logger.debug(f"Fetched {self.model.__name__} id={id}")
            return instance
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error in get_by_id: {e}")
            raise DBError(message=str(e), details={"error": str(e)})

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        """List records with optional filters, pagination via offset and limit."""
        try:
            # Avoid mutable default for filters
            filters = filters or {}
            stmt = select(self.model)
            if filters:
                stmt = stmt.filter_by(**filters)
            stmt = stmt.offset(offset).limit(limit)
            result = await self.session.execute(stmt)
            items = result.scalars().all()
            self.logger.debug(f"Listed {len(items)} items of {self.model.__name__}")
            return items
        except Exception as e:
            self.logger.error(f"Error in list: {e}")
            raise DBError(message=str(e), details={"error": str(e)})

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Return the total number of records, optionally filtered."""
        try:
            filters = filters or {}
            stmt = select(func.count()).select_from(self.model)
            if filters:
                stmt = stmt.filter_by(**filters)
            result = await self.session.execute(stmt)
            total = result.scalar_one()
            self.logger.debug(f"Counted {total} items of {self.model.__name__}")
            return total
        except Exception as e:
            self.logger.error(f"Error in count: {e}")
            raise DBError(message=str(e), details={"error": str(e)})

    async def create(self, data: Dict[str, Any]) -> ModelType:
        """Create a new record from provided data dict."""
        try:
            obj = self.model(**data)  # type: ignore
            self.session.add(obj)
            await self.session.flush()
            self.logger.debug(
                f"Created {self.model.__name__} id={getattr(obj, 'id', None)}"
            )
            return obj
        except Exception as e:
            self.logger.error(f"Error in create: {e}")
            raise DBError(message=str(e), details={"error": str(e)})

    async def update(self, id: Any, data: Dict[str, Any]) -> ModelType:
        """Update an existing record by id with provided data dict."""
        try:
            instance = await self.get_by_id(id)
            for key, value in data.items():
                setattr(instance, key, value)
            await self.session.flush()
            self.logger.debug(f"Updated {self.model.__name__} id={id}")
            return instance
        except Exception as e:
            self.logger.error(f"Error in update: {e}")
            raise DBError(message=str(e), details={"error": str(e)})

    async def delete(self, id: Any) -> None:
        """Delete a record by primary key id."""
        try:
            instance = await self.get_by_id(id)
            await self.session.delete(instance)
            await self.session.flush()
            self.logger.debug(f"Deleted {self.model.__name__} id={id}")
        except Exception as e:
            self.logger.error(f"Error in delete: {e}")
            raise DBError(message=str(e), details={"error": str(e)})
