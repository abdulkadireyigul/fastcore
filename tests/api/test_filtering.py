"""
Tests for the filtering module.

This module contains tests for the filtering utilities, including
FilterOperator, FilterCondition, and FilterParams classes.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from fastcore.api.filtering import FilterCondition, FilterOperator, FilterParams


class TestFilterOperator:
    """Tests for the FilterOperator enum."""

    def test_values(self):
        """Test that enum values are correct."""
        assert FilterOperator.EQ == "eq"
        assert FilterOperator.NE == "ne"
        assert FilterOperator.GT == "gt"
        assert FilterOperator.GE == "ge"
        assert FilterOperator.LT == "lt"
        assert FilterOperator.LE == "le"
        assert FilterOperator.IN == "in"
        assert FilterOperator.NOT_IN == "not_in"
        assert FilterOperator.LIKE == "like"
        assert FilterOperator.ILIKE == "ilike"
        assert FilterOperator.IS_NULL == "is_null"
        assert FilterOperator.IS_NOT_NULL == "is_not_null"


class TestFilterCondition:
    """Tests for the FilterCondition class."""

    def test_init_with_value(self):
        """Test initialization with value."""
        condition = FilterCondition("name", FilterOperator.EQ, "Alice")
        assert condition.field == "name"
        assert condition.operator == FilterOperator.EQ
        assert condition.value == "Alice"

    def test_init_without_value(self):
        """Test initialization without value for null operators."""
        condition = FilterCondition("name", FilterOperator.IS_NULL)
        assert condition.field == "name"
        assert condition.operator == FilterOperator.IS_NULL
        assert condition.value is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        condition = FilterCondition("name", FilterOperator.EQ, "Alice")
        assert condition.to_dict() == {
            "field": "name",
            "operator": "eq",
            "value": "Alice",
        }

    def test_string_representation_with_value(self):
        """Test string representation with value."""
        condition = FilterCondition("name", FilterOperator.EQ, "Alice")
        assert str(condition) == "name:eq:Alice"

    def test_string_representation_without_value(self):
        """Test string representation without value."""
        condition = FilterCondition("name", FilterOperator.IS_NULL)
        assert str(condition) == "name:is_null"

    def test_repr(self):
        """Test representation."""
        condition = FilterCondition("name", FilterOperator.EQ, "Alice")
        assert (
            repr(condition)
            == "FilterCondition(field='name', operator=FilterOperator.EQ, value='Alice')"
        )


class TestFilterParams:
    """Tests for the FilterParams class."""

    def test_init_empty(self):
        """Test initialization with no parameters."""
        filter_params = FilterParams()()
        assert filter_params.filters == []
        assert filter_params.allowed_fields is None

    def test_init_with_allowed_fields(self):
        """Test initialization with allowed fields."""
        allowed_fields = {"name", "age", "status"}
        filter_params = FilterParams(allowed_fields=allowed_fields)()
        assert filter_params.filters == []
        assert filter_params.allowed_fields == allowed_fields

    def test_parse_filter_strings_with_value(self):
        """Test parsing filter strings with value."""
        filter_params = FilterParams()(filter=["name:eq:Alice"])
        assert len(filter_params.filters) == 1

        condition = filter_params.filters[0]
        assert condition.field == "name"
        assert condition.operator == FilterOperator.EQ
        assert condition.value == "Alice"

    def test_parse_filter_strings_without_value(self):
        """Test parsing filter strings without value."""
        filter_params = FilterParams()(filter=["name:is_null"])
        assert len(filter_params.filters) == 1

        condition = filter_params.filters[0]
        assert condition.field == "name"
        assert condition.operator == FilterOperator.IS_NULL
        assert condition.value is None

    def test_parse_filter_strings_with_colon_in_value(self):
        """Test parsing filter strings with colons in value."""
        filter_params = FilterParams()(filter=["timestamp:gt:2023-01-01T12:30:45"])
        assert len(filter_params.filters) == 1

        condition = filter_params.filters[0]
        assert condition.field == "timestamp"
        assert condition.operator == FilterOperator.GT
        assert condition.value == "2023-01-01T12:30:45"

    def test_parse_filter_strings_with_in_operator(self):
        """Test parsing filter strings with IN operator."""
        filter_params = FilterParams()(filter=["status:in:active,pending,draft"])
        assert len(filter_params.filters) == 1

        condition = filter_params.filters[0]
        assert condition.field == "status"
        assert condition.operator == FilterOperator.IN
        assert condition.value == ["active", "pending", "draft"]

    def test_validate_allowed_fields_valid(self):
        """Test validation with valid fields."""
        filter_params = FilterParams(allowed_fields={"name", "age"})(
            filter=["name:eq:Alice", "age:gt:25"]
        )
        assert len(filter_params.filters) == 2

    def test_validate_allowed_fields_invalid(self):
        """Test validation with invalid fields."""
        with pytest.raises(ValueError) as excinfo:
            FilterParams(allowed_fields={"name", "age"})(
                filter=["email:eq:alice@example.com"]
            )

        assert "Invalid filter field: email" in str(excinfo.value)
        assert "Allowed fields are: age, name" in str(excinfo.value)

    def test_validate_operator_invalid(self):
        """Test validation with invalid operator."""
        with pytest.raises(ValueError) as excinfo:
            FilterParams()(filter=["name:invalid:Alice"])

        assert "Invalid filter operator: invalid" in str(excinfo.value)

    def test_validate_missing_value(self):
        """Test validation with missing value."""
        with pytest.raises(ValueError) as excinfo:
            FilterParams()(filter=["name:eq"])

        assert "Missing value for filter: name:eq" in str(excinfo.value)

    def test_validate_invalid_format(self):
        """Test validation with invalid format."""
        with pytest.raises(ValueError) as excinfo:
            FilterParams()(filter=["name"])

        assert "Invalid filter format: name" in str(excinfo.value)

    def test_get_filter_conditions(self):
        """Test getting filter conditions."""
        filter_params = FilterParams()(filter=["name:eq:Alice", "age:gt:25"])
        conditions = filter_params.get_filter_conditions()

        assert len(conditions) == 2
        assert conditions[0].field == "name"
        assert conditions[0].operator == FilterOperator.EQ
        assert conditions[0].value == "Alice"

        assert conditions[1].field == "age"
        assert conditions[1].operator == FilterOperator.GT
        assert conditions[1].value == "25"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        filter_params = FilterParams()(filter=["name:eq:Alice", "age:gt:25"])
        result = filter_params.to_dict()

        assert result == {
            "filters": [
                {"field": "name", "operator": "eq", "value": "Alice"},
                {"field": "age", "operator": "gt", "value": "25"},
            ]
        }

    def test_default_filters(self):
        """Test using default filters when no filters are provided."""
        default_filters = [
            {"field": "status", "operator": "eq", "value": "active"},
            {"field": "deleted", "operator": "is_null"},
        ]

        filter_params = FilterParams(default_filters=default_filters)()

        assert len(filter_params.filters) == 2
        assert filter_params.filters[0].field == "status"
        assert filter_params.filters[0].operator == FilterOperator.EQ
        assert filter_params.filters[0].value == "active"

        assert filter_params.filters[1].field == "deleted"
        assert filter_params.filters[1].operator == FilterOperator.IS_NULL


# Setup for SQLAlchemy-related tests
Base = declarative_base()


class SQLModel(Base):
    """Test model for SQLAlchemy tests."""

    __tablename__ = "test_model"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    status = Column(String)


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Add test data
    session.add(SQLModel(id=1, name="Alice", age=30, status="active"))
    session.add(SQLModel(id=2, name="Bob", age=25, status="inactive"))
    session.add(SQLModel(id=3, name="Charlie", age=35, status="active"))
    session.add(SQLModel(id=4, name="David", age=20, status="pending"))
    session.add(SQLModel(id=5, name="Eve", age=28, status=None))
    session.commit()

    yield session
    session.close()


class TestSQLAlchemyIntegration:
    """Tests for SQLAlchemy integration."""

    def test_apply_eq_filter(self, db_session):
        """Test applying an equal filter to a query."""
        filter_params = FilterParams()(filter=["name:eq:Alice"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 1
        assert results[0].name == "Alice"

    def test_apply_ne_filter(self, db_session):
        """Test applying a not equal filter to a query."""
        filter_params = FilterParams()(filter=["status:ne:active"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        # Should include Bob, David, and Eve (null status)
        assert len(results) == 3
        statuses = [r.status for r in results]
        assert "active" not in statuses

    def test_apply_gt_filter(self, db_session):
        """Test applying a greater than filter to a query."""
        filter_params = FilterParams()(filter=["age:gt:28"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 2
        ages = [r.age for r in results]
        assert all(age > 28 for age in ages)
        names = [r.name for r in results]
        assert "Alice" in names
        assert "Charlie" in names

    def test_apply_ge_filter(self, db_session):
        """Test applying a greater than or equal filter to a query."""
        filter_params = FilterParams()(filter=["age:ge:30"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 2
        ages = [r.age for r in results]
        assert all(age >= 30 for age in ages)

    def test_apply_lt_filter(self, db_session):
        """Test applying a less than filter to a query."""
        filter_params = FilterParams()(filter=["age:lt:25"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 1
        assert results[0].name == "David"
        assert results[0].age == 20

    def test_apply_le_filter(self, db_session):
        """Test applying a less than or equal filter to a query."""
        filter_params = FilterParams()(filter=["age:le:25"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 2
        ages = [r.age for r in results]
        assert all(age <= 25 for age in ages)

    def test_apply_in_filter(self, db_session):
        """Test applying an in filter to a query."""
        filter_params = FilterParams()(filter=["status:in:active,pending"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 3
        statuses = [r.status for r in results]
        assert all(status in ["active", "pending"] for status in statuses)

    def test_apply_not_in_filter(self, db_session):
        """Test applying a not in filter to a query."""
        filter_params = FilterParams()(filter=["status:not_in:active,pending"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 2
        statuses = [r.status for r in results if r.status is not None]
        assert all(status not in ["active", "pending"] for status in statuses)

    def test_apply_like_filter(self, db_session):
        """Test applying a like filter to a query."""
        filter_params = FilterParams()(filter=["name:like:A%"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 1
        assert results[0].name == "Alice"

    def test_apply_ilike_filter(self, db_session):
        """Test applying a case-insensitive like filter to a query."""
        filter_params = FilterParams()(filter=["name:ilike:a%"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 1
        assert results[0].name == "Alice"

    def test_apply_is_null_filter(self, db_session):
        """Test applying an is null filter to a query."""
        filter_params = FilterParams()(filter=["status:is_null"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 1
        assert results[0].name == "Eve"
        assert results[0].status is None

    def test_apply_is_not_null_filter(self, db_session):
        """Test applying an is not null filter to a query."""
        filter_params = FilterParams()(filter=["status:is_not_null"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 4
        assert all(r.status is not None for r in results)

    def test_apply_multiple_filters(self, db_session):
        """Test applying multiple filters to a query."""
        filter_params = FilterParams()(filter=["status:eq:active", "age:gt:30"])
        query = db_session.query(SQLModel)
        filtered_query = filter_params.apply(query, SQLModel)
        results = filtered_query.all()

        assert len(results) == 1
        assert results[0].name == "Charlie"
        assert results[0].status == "active"
        assert results[0].age == 35


class TestFastAPIIntegration:
    """Tests for FastAPI integration."""

    def test_filter_params_dependency(self):
        """Test using FilterParams as a dependency in FastAPI."""
        app = FastAPI()

        @app.get("/test")
        def read_test(
            filters: FilterParams = Depends(
                FilterParams(allowed_fields={"name", "age", "status"})
            )
        ):
            return {
                "filters": [
                    str(condition) for condition in filters.get_filter_conditions()
                ]
            }

        # Register exception handler to convert ValueError to HTTPException
        @app.exception_handler(ValueError)
        async def value_error_handler(request, exc):
            return JSONResponse(
                status_code=422,
                content={"detail": str(exc)},
            )

        client = TestClient(app)

        # Test with no parameters (empty filters)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"filters": []}

        # Test with single filter parameter
        response = client.get("/test?filter=name:eq:Alice")
        assert response.status_code == 200
        assert response.json() == {"filters": ["name:eq:Alice"]}

        # Test with multiple filter parameters
        response = client.get("/test?filter=name:eq:Alice&filter=age:gt:25")
        assert response.status_code == 200
        assert response.json() == {"filters": ["name:eq:Alice", "age:gt:25"]}

        # Test with invalid field
        response = client.get("/test?filter=email:eq:alice@example.com")
        assert response.status_code == 422
        assert "Invalid filter field: email" in response.json()["detail"]
