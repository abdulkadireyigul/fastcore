"""
Tests for the sorting module.

This module contains tests for the sorting utilities, including
SortDirection, SortField, and SortParams classes.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from fastcore.api.sorting import SortDirection, SortField, SortParams


class TestSortDirection:
    """Tests for the SortDirection enum."""

    def test_values(self):
        """Test that enum values are correct."""
        assert SortDirection.ASC == "asc"
        assert SortDirection.DESC == "desc"


class TestSortField:
    """Tests for the SortField class."""

    def test_init(self):
        """Test initialization with default direction."""
        field = SortField("name")
        assert field.field == "name"
        assert field.direction == SortDirection.ASC

    def test_init_with_direction(self):
        """Test initialization with specified direction."""
        field = SortField("name", SortDirection.DESC)
        assert field.field == "name"
        assert field.direction == SortDirection.DESC

    def test_parse_field_only(self):
        """Test parsing a string with just the field name."""
        field = SortField.parse("name")
        assert field.field == "name"
        assert field.direction == SortDirection.ASC

    def test_parse_field_and_direction(self):
        """Test parsing a string with field name and direction."""
        field = SortField.parse("name:desc")
        assert field.field == "name"
        assert field.direction == SortDirection.DESC

    def test_parse_invalid_direction(self):
        """Test parsing a string with an invalid direction."""
        # Should default to ASC for invalid direction
        field = SortField.parse("name:invalid")
        assert field.field == "name"
        assert field.direction == SortDirection.ASC

    def test_to_dict(self):
        """Test conversion to dictionary."""
        field = SortField("name", SortDirection.DESC)
        assert field.to_dict() == {"field": "name", "direction": "desc"}

    def test_string_representation(self):
        """Test string representation."""
        field = SortField("name", SortDirection.DESC)
        assert str(field) == "name:desc"

    def test_repr(self):
        """Test representation."""
        field = SortField("name", SortDirection.DESC)
        assert repr(field) == "SortField(field='name', direction=SortDirection.DESC)"


class TestSortParams:
    """Tests for the SortParams class."""

    def test_init_empty(self):
        """Test initialization with no parameters."""
        sorter = SortParams()()
        assert sorter.sort_by == []
        assert sorter.allowed_fields is None

    def test_init_with_allowed_fields(self):
        """Test initialization with allowed fields."""
        allowed_fields = {"name", "age", "created_at"}
        sorter = SortParams(allowed_fields=allowed_fields)()
        assert sorter.sort_by == []
        assert sorter.allowed_fields == allowed_fields

    def test_init_with_default_sort(self):
        """Test initialization with default sort."""
        sorter = SortParams(default_sort="name:asc")()
        assert len(sorter.sort_by) == 1
        assert sorter.sort_by[0].field == "name"
        assert sorter.sort_by[0].direction == SortDirection.ASC

    def test_parse_sort_strings(self):
        """Test parsing sort strings."""
        sorter = SortParams()(sort_by=["name:asc", "age:desc"])
        assert len(sorter.sort_by) == 2

        assert sorter.sort_by[0].field == "name"
        assert sorter.sort_by[0].direction == SortDirection.ASC

        assert sorter.sort_by[1].field == "age"
        assert sorter.sort_by[1].direction == SortDirection.DESC

    def test_validate_allowed_fields_valid(self):
        """Test validation with valid fields."""
        sorter = SortParams(allowed_fields={"name", "age"})(
            sort_by=["name:asc", "age:desc"]
        )
        assert len(sorter.sort_by) == 2

    def test_validate_allowed_fields_invalid(self):
        """Test validation with invalid fields."""
        with pytest.raises(ValueError) as excinfo:
            SortParams(allowed_fields={"name", "age"})(sort_by=["email:asc"])

        assert "Invalid sort field: email" in str(excinfo.value)
        assert "Allowed fields are: age, name" in str(excinfo.value)

    def test_get_sort_fields(self):
        """Test getting sort fields."""
        sorter = SortParams()(sort_by=["name:asc", "age:desc"])
        fields = sorter.get_sort_fields()

        assert len(fields) == 2
        assert fields[0].field == "name"
        assert fields[0].direction == SortDirection.ASC
        assert fields[1].field == "age"
        assert fields[1].direction == SortDirection.DESC

    def test_to_dict(self):
        """Test conversion to dictionary."""
        sorter = SortParams()(sort_by=["name:asc", "age:desc"])
        result = sorter.to_dict()

        assert result == {
            "sort_by": [
                {"field": "name", "direction": "asc"},
                {"field": "age", "direction": "desc"},
            ]
        }


# Setup for SQLAlchemy-related tests
Base = declarative_base()


class SQLModel(Base):
    """Test model for SQLAlchemy tests."""

    __tablename__ = "test_model"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    created_at = Column(String)


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Add test data
    session.add(SQLModel(id=1, name="Alice", age=30))
    session.add(SQLModel(id=2, name="Bob", age=25))
    session.add(SQLModel(id=3, name="Charlie", age=35))
    session.add(SQLModel(id=4, name="David", age=20))
    session.commit()

    yield session
    session.close()


class TestSQLAlchemyIntegration:
    """Tests for SQLAlchemy integration."""

    def test_apply_single_sort(self, db_session):
        """Test applying a single sort to a query."""
        sorter = SortParams()(sort_by=["name:asc"])
        query = db_session.query(SQLModel)
        sorted_query = sorter.apply(query, SQLModel)
        results = sorted_query.all()

        assert len(results) == 4
        assert results[0].name == "Alice"
        assert results[1].name == "Bob"
        assert results[2].name == "Charlie"
        assert results[3].name == "David"

    def test_apply_multiple_sorts(self, db_session):
        """Test applying multiple sorts to a query."""
        # Add users with duplicate ages to test multiple sort criteria
        db_session.add(SQLModel(id=5, name="Eve", age=30))
        db_session.commit()

        # Sort by age ascending, then by name descending
        sorter = SortParams()(sort_by=["age:asc", "name:desc"])
        query = db_session.query(SQLModel)
        sorted_query = sorter.apply(query, SQLModel)
        results = sorted_query.all()

        assert len(results) == 5
        assert results[0].age == 20  # David
        assert results[1].age == 25  # Bob

        # For age 30, should be sorted by name in descending order
        age_30_names = [r.name for r in results if r.age == 30]
        assert age_30_names == ["Eve", "Alice"]

        assert results[4].age == 35  # Charlie

    def test_apply_descending_sort(self, db_session):
        """Test applying a descending sort to a query."""
        sorter = SortParams()(sort_by=["age:desc"])
        query = db_session.query(SQLModel)
        sorted_query = sorter.apply(query, SQLModel)
        results = sorted_query.all()

        assert len(results) == 4
        assert results[0].age == 35  # Charlie
        assert results[1].age == 30  # Alice
        assert results[2].age == 25  # Bob
        assert results[3].age == 20  # David

    def test_get_order_by(self):
        """Test getting order by expressions."""
        sorter = SortParams()(sort_by=["name:asc", "age:desc"])
        order_by_clauses = sorter.get_order_by(SQLModel)

        assert len(order_by_clauses) == 2
        # Can't directly test the SQLAlchemy expressions, but can verify count


class TestFastAPIIntegration:
    """Tests for FastAPI integration."""

    def test_sort_params_dependency(self):
        """Test using SortParams as a dependency in FastAPI."""
        app = FastAPI()

        @app.get("/test")
        def read_test(
            sort: SortParams = Depends(SortParams(allowed_fields={"name", "age"}))
        ):
            return {"sort_fields": [str(field) for field in sort.get_sort_fields()]}

        # Register exception handler to convert ValueError to HTTPException
        @app.exception_handler(ValueError)
        async def value_error_handler(request, exc):
            return JSONResponse(
                status_code=422,
                content={"detail": str(exc)},
            )

        client = TestClient(app)

        # Test with no parameters (empty sort)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"sort_fields": []}

        # Test with single sort parameter
        response = client.get("/test?sort_by=name:asc")
        assert response.status_code == 200
        assert response.json() == {"sort_fields": ["name:asc"]}

        # Test with multiple sort parameters
        response = client.get("/test?sort_by=name:asc&sort_by=age:desc")
        assert response.status_code == 200
        assert response.json() == {"sort_fields": ["name:asc", "age:desc"]}

        # Test with invalid field
        response = client.get("/test?sort_by=email:asc")
        assert response.status_code == 422
        assert "Invalid sort field: email" in response.json()["detail"]
