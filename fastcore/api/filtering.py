"""
Filtering utilities for FastAPI applications.

This module provides standardized filtering functionality for API endpoints,
including request parameters and database query helpers for SQLAlchemy.
"""

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi import Query
from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query as SQLAQuery

T = TypeVar("T")


class FilterOperator(str, Enum):
    """
    Filter operators for field comparisons.

    Attributes:
        EQ: Equal to
        NE: Not equal to
        GT: Greater than
        GE: Greater than or equal to
        LT: Less than
        LE: Less than or equal to
        IN: In a list of values
        NOT_IN: Not in a list of values
        LIKE: Pattern matching (SQL LIKE)
        ILIKE: Case-insensitive pattern matching
        IS_NULL: Is NULL
        IS_NOT_NULL: Is not NULL
    """

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    ILIKE = "ilike"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class FilterCondition:
    """
    Filter condition for a field.

    This class represents a filter condition on a specific field,
    including the operator and value to compare with.

    Attributes:
        field: Field name to filter on
        operator: Filter operator
        value: Value to compare with
    """

    def __init__(self, field: str, operator: FilterOperator, value: Any = None):
        """
        Initialize filter condition.

        Args:
            field: Field name to filter on
            operator: Filter operator
            value: Value to compare with (not used for IS_NULL, IS_NOT_NULL)
        """
        self.field = field
        self.operator = operator
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert filter condition to dictionary.

        Returns:
            Dictionary with field, operator, and value
        """
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
        }

    def __str__(self) -> str:
        if self.operator in (FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL):
            return f"{self.field}:{self.operator.value}"
        return f"{self.field}:{self.operator.value}:{self.value}"

    def __repr__(self) -> str:
        return (
            f"FilterCondition(field='{self.field}', "
            f"operator={self.operator}, value={repr(self.value)})"
        )


class FilterParams:
    """
    Query parameters for filtering.

    This class is designed to be used as a dependency in FastAPI route functions
    to provide standardized filtering parameters.

    Attributes:
        filters: List of filter conditions
        allowed_fields: Set of allowed field names to filter on

    Example:
        ```python
        @app.get("/items/")
        def get_items(
            filters: FilterParams = Depends(
                FilterParams(allowed_fields={"id", "name", "status"})
            )
        ):
            query = db.query(Item)
            query = filters.apply(query, Item)
            return query.all()
        ```
    """

    def __init__(
        self,
        allowed_fields: Optional[set[str]] = None,
        default_filters: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize filter parameters factory.

        Args:
            allowed_fields: Set of allowed field names to filter on
            default_filters: Default filters to apply if none provided
        """
        self.allowed_fields = allowed_fields
        self.default_filters = default_filters

    def __call__(
        self,
        filter: Optional[List[str]] = Query(
            None,
            description=(
                "Filter conditions in format 'field:operator:value'. "
                "Example: 'status:eq:active' or 'created_at:gt:2023-01-01'"
            ),
            examples=["status:eq:active", "price:gt:100"],
        ),
    ) -> "FilterParams":
        """
        Create filter parameters from query parameters.

        Args:
            filter: List of filter strings in format "field:operator:value"

        Returns:
            Initialized FilterParams instance

        Raises:
            ValueError: If an invalid filter field or operator is provided
        """
        instance = self.__new__(FilterParams)

        # Parse filter conditions
        conditions: List[FilterCondition] = []

        # Get actual value from Query if needed
        filter_value = getattr(filter, "default", filter)

        # Use default filters if provided and no filter
        parsed_filters = filter_value or []
        if not parsed_filters and self.default_filters:
            # Convert default filters to string format
            for f in self.default_filters:
                if all(k in f for k in ["field", "operator"]):
                    field = f["field"]
                    operator = f["operator"]
                    value = f.get("value")

                    if operator in (
                        FilterOperator.IS_NULL.value,
                        FilterOperator.IS_NOT_NULL.value,
                    ):
                        parsed_filters.append(f"{field}:{operator}")
                    else:
                        parsed_filters.append(f"{field}:{operator}:{value}")

        for filter_string in parsed_filters:
            parts = filter_string.split(":")

            if len(parts) < 2:
                raise ValueError(
                    f"Invalid filter format: {filter_string}. "
                    f"Expected format: field:operator:value"
                )

            field = parts[0].strip()
            operator_str = parts[1].strip()

            # Validate field name if allowed_fields is provided
            if self.allowed_fields and field not in self.allowed_fields:
                valid_fields = ", ".join(sorted(self.allowed_fields))
                raise ValueError(
                    f"Invalid filter field: {field}. "
                    f"Allowed fields are: {valid_fields}"
                )

            # Parse and validate operator
            try:
                operator = FilterOperator(operator_str)
            except ValueError:
                valid_operators = ", ".join([op.value for op in FilterOperator])
                raise ValueError(
                    f"Invalid filter operator: {operator_str}. "
                    f"Allowed operators are: {valid_operators}"
                )

            # Handle operators that don't need a value
            if operator in (FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL):
                conditions.append(FilterCondition(field, operator))
            else:
                # All other operators need a value
                if len(parts) < 3:
                    raise ValueError(
                        f"Missing value for filter: {filter_string}. "
                        f"Expected format: field:operator:value"
                    )

                value = parts[2]
                for i in range(3, len(parts)):
                    value += ":" + parts[i]

                # Handle list values for IN and NOT_IN operators
                if operator in (FilterOperator.IN, FilterOperator.NOT_IN):
                    value = [v.strip() for v in value.split(",")]

                conditions.append(FilterCondition(field, operator, value))

        instance.filters = conditions
        instance.allowed_fields = self.allowed_fields
        return instance

    def get_filter_conditions(self) -> List[FilterCondition]:
        """
        Get list of filter conditions.

        Returns:
            List of filter conditions
        """
        return self.filters

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert filter parameters to dictionary.

        Returns:
            Dictionary with filters key containing list of filter conditions
        """
        return {"filters": [f.to_dict() for f in self.filters]}

    def apply(self, query: SQLAQuery, model: Any) -> SQLAQuery:
        """
        Apply filtering to a SQLAlchemy query.

        This method adds WHERE clauses to the query based on the filter conditions.

        Args:
            query: SQLAlchemy query to apply filtering to
            model: SQLAlchemy model class

        Returns:
            SQLAlchemy query with filtering applied

        Example:
            ```python
            query = db.query(Item)
            query = filter_params.apply(query, Item)
            items = query.all()
            ```
        """
        if not self.filters:
            return query

        for condition in self.filters:
            # Skip unknown fields
            if not hasattr(model, condition.field):
                continue

            column = getattr(model, condition.field)

            if condition.operator == FilterOperator.EQ:
                query = query.filter(column == condition.value)
            elif condition.operator == FilterOperator.NE:
                # For NE, need to handle NULL values specially
                query = query.filter(or_(column != condition.value, column.is_(None)))
            elif condition.operator == FilterOperator.GT:
                query = query.filter(column > condition.value)
            elif condition.operator == FilterOperator.GE:
                query = query.filter(column >= condition.value)
            elif condition.operator == FilterOperator.LT:
                query = query.filter(column < condition.value)
            elif condition.operator == FilterOperator.LE:
                query = query.filter(column <= condition.value)
            elif condition.operator == FilterOperator.IN:
                query = query.filter(column.in_(condition.value))
            elif condition.operator == FilterOperator.NOT_IN:
                # For NOT_IN, need to handle NULL values specially
                query = query.filter(
                    or_(column.notin_(condition.value), column.is_(None))
                )
            elif condition.operator == FilterOperator.LIKE:
                query = query.filter(column.like(condition.value))
            elif condition.operator == FilterOperator.ILIKE:
                query = query.filter(column.ilike(condition.value))
            elif condition.operator == FilterOperator.IS_NULL:
                query = query.filter(column.is_(None))
            elif condition.operator == FilterOperator.IS_NOT_NULL:
                query = query.filter(column.isnot(None))

        return query
