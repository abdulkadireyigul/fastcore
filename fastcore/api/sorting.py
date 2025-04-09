"""
Sorting utilities for FastAPI applications.

This module provides standardized sorting functionality for API endpoints,
including request parameters and database query helpers for SQLAlchemy.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import Query
from sqlalchemy import Column, asc, desc
from sqlalchemy.orm import Query as SQLAQuery


class SortDirection(str, Enum):
    """
    Sort direction enum.

    Attributes:
        ASC: Ascending order
        DESC: Descending order
    """

    ASC = "asc"
    DESC = "desc"


class SortField:
    """
    Sort field definition.

    This class represents a field to sort by, including the field name
    and sort direction.

    Attributes:
        field: Field name to sort by
        direction: Sort direction (asc or desc)
    """

    def __init__(self, field: str, direction: SortDirection = SortDirection.ASC):
        """
        Initialize sort field.

        Args:
            field: Field name to sort by
            direction: Sort direction
        """
        self.field = field
        self.direction = direction

    @classmethod
    def parse(cls, sort_string: str) -> "SortField":
        """
        Parse a sort string in format "field:direction".

        Args:
            sort_string: String in format "field" or "field:direction"

        Returns:
            SortField instance

        Examples:
            >>> SortField.parse("name")
            SortField(field="name", direction=SortDirection.ASC)
            >>> SortField.parse("name:desc")
            SortField(field="name", direction=SortDirection.DESC)
        """
        parts = sort_string.split(":")
        field = parts[0].strip()

        if len(parts) > 1:
            try:
                direction = SortDirection(parts[1].lower())
            except ValueError:
                direction = SortDirection.ASC
        else:
            direction = SortDirection.ASC

        return cls(field, direction)

    def to_dict(self) -> Dict[str, str]:
        """
        Convert sort field to dictionary.

        Returns:
            Dictionary with field and direction
        """
        return {"field": self.field, "direction": self.direction.value}

    def __str__(self) -> str:
        return f"{self.field}:{self.direction.value}"

    def __repr__(self) -> str:
        return f"SortField(field='{self.field}', direction={self.direction})"


class SortParams:
    """
    Query parameters for sorting.

    This class is designed to be used as a dependency in FastAPI route functions
    to provide standardized sorting parameters.

    Attributes:
        sort_by: List of sort fields
        allowed_fields: Set of allowed field names to sort by

    Example:
        ```python
        @app.get("/items/")
        def get_items(
            sort: SortParams = Depends(SortParams(allowed_fields={"id", "name", "created_at"}))
        ):
            query = db.query(Item)
            query = sort.apply(query, Item)
            return query.all()
        ```
    """

    def __init__(
        self,
        allowed_fields: Optional[set[str]] = None,
        default_sort: Optional[str] = None,
    ):
        """
        Initialize sort parameters factory.

        Args:
            allowed_fields: Set of allowed field names to sort by
            default_sort: Default sort string in format "field:direction"
        """
        self.allowed_fields = allowed_fields
        self.default_sort = default_sort

    def __call__(
        self,
        sort_by: Optional[List[str]] = Query(
            None,
            description=(
                "Fields to sort by, in format 'field:direction' or just 'field' "
                "(defaults to ascending). Example: 'name' or 'created_at:desc'"
            ),
            examples=["name:asc", "created_at:desc"],
        ),
    ) -> "SortParams":
        """
        Create sort parameters from query parameters.

        Args:
            sort_by: List of sort strings in format "field:direction"

        Returns:
            Initialized SortParams instance

        Raises:
            ValueError: If an invalid sort field is provided
        """
        instance = self.__new__(SortParams)

        # Parse sort fields
        parsed_fields: List[SortField] = []

        # Get actual value from Query if needed
        sort_by_value = getattr(sort_by, "default", sort_by)

        # Use default sort if provided and no sort_by
        if not sort_by_value and self.default_sort:
            sort_by_value = [self.default_sort]

        if sort_by_value:
            for sort_string in sort_by_value:
                sort_field = SortField.parse(sort_string)

                # Validate field name if allowed_fields is provided
                if self.allowed_fields and sort_field.field not in self.allowed_fields:
                    valid_fields = ", ".join(sorted(self.allowed_fields))
                    raise ValueError(
                        f"Invalid sort field: {sort_field.field}. "
                        f"Allowed fields are: {valid_fields}"
                    )

                parsed_fields.append(sort_field)

        instance.sort_by = parsed_fields
        instance.allowed_fields = self.allowed_fields
        return instance

    def get_sort_fields(self) -> List[SortField]:
        """
        Get list of sort fields.

        Returns:
            List of sort fields
        """
        return self.sort_by

    def to_dict(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Convert sort parameters to dictionary.

        Returns:
            Dictionary with sort_by key containing list of sort fields
        """
        return {"sort_by": [field.to_dict() for field in self.sort_by]}

    def apply(self, query: SQLAQuery, model: Any) -> SQLAQuery:
        """
        Apply sorting to a SQLAlchemy query.

        This method adds ORDER BY clauses to the query based on the sort parameters.

        Args:
            query: SQLAlchemy query to apply sorting to
            model: SQLAlchemy model class

        Returns:
            SQLAlchemy query with sorting applied

        Example:
            ```python
            query = db.query(Item)
            query = sort_params.apply(query, Item)
            items = query.all()
            ```
        """
        if not self.sort_by:
            return query

        for sort_field in self.sort_by:
            # Skip unknown fields (should already be validated in __call__)
            if not hasattr(model, sort_field.field):
                continue

            column = getattr(model, sort_field.field)

            if sort_field.direction == SortDirection.DESC:
                query = query.order_by(desc(column))
            else:
                query = query.order_by(asc(column))

        return query

    def get_order_by(self, model: Any) -> List[Any]:
        """
        Get SQLAlchemy order_by expressions.

        This method creates order_by expressions that can be used with
        SQLAlchemy's order_by() function.

        Args:
            model: SQLAlchemy model class

        Returns:
            List of SQLAlchemy order_by expressions
        """
        order_by_clauses = []

        for sort_field in self.sort_by:
            if not hasattr(model, sort_field.field):
                continue

            column = getattr(model, sort_field.field)

            if sort_field.direction == SortDirection.DESC:
                order_by_clauses.append(desc(column))
            else:
                order_by_clauses.append(asc(column))

        return order_by_clauses
