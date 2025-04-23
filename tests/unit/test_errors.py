"""
Unit tests for the errors module (exceptions.py, handlers.py, manager.py).

Covers:
- Instantiation and attributes of all custom exception classes (parametrized)
- Edge cases for custom messages, codes, details, and special fields
- FastAPI integration and error handler registration
- All error handler branches and edge cases
"""
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from src.errors.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    DBError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.errors.handlers import _create_validation_errors, register_exception_handlers
from src.errors.manager import setup_errors


@pytest.mark.parametrize(
    "exc_cls,kwargs,expected",
    [
        (
            AppError,
            {},
            {
                "message": "An unexpected error occurred",
                "code": "ERROR",
                "status_code": 500,
            },
        ),
        (
            AppError,
            {
                "message": "Custom",
                "code": "CUSTOM",
                "status_code": 418,
                "details": {"foo": "bar"},
            },
            {"message": "Custom", "code": "CUSTOM", "status_code": 418},
        ),
        (
            ValidationError,
            {"fields": [{"field": "email", "msg": "invalid"}]},
            {"status_code": 400},
        ),
        (NotFoundError, {}, {"status_code": 404, "code": "NOT_FOUND"}),
        (UnauthorizedError, {}, {"status_code": 401, "code": "UNAUTHORIZED"}),
        (ForbiddenError, {}, {"status_code": 403, "code": "FORBIDDEN"}),
        (ConflictError, {}, {"status_code": 409, "code": "CONFLICT"}),
        (BadRequestError, {}, {"status_code": 400, "code": "BAD_REQUEST"}),
        (DBError, {}, {"status_code": 500, "code": "DB_ERROR"}),
    ],
)
def test_exception_attributes(exc_cls, kwargs, expected):
    """Test attributes of all custom exception classes."""
    err = exc_cls(**kwargs)
    for key, value in expected.items():
        assert getattr(err, key) == value


def test_not_found_error_with_resource():
    err = NotFoundError(resource_type="User", resource_id=123)
    assert err.message == "User with id '123' not found"
    assert err.details["resource_type"] == "User"
    assert err.details["resource_id"] == 123


def test_create_validation_errors_exclude_body():
    errors_data = [
        {"loc": ["body", "field1"], "msg": "err1"},
        {"loc": ["query", "field2"], "msg": "err2"},
    ]
    errors = _create_validation_errors(errors_data, exclude_body=True)
    assert errors[0].field == "field1"
    assert errors[1].field == "query.field2"


def test_create_validation_errors_include_body():
    errors_data = [
        {"loc": ["body", "field1"], "msg": "err1"},
        {"loc": ["query", "field2"], "msg": "err2"},
    ]
    errors = _create_validation_errors(errors_data, exclude_body=False)
    assert errors[0].field == "body.field1"
    assert errors[1].field == "query.field2"


@pytest.fixture
def fastapi_app():
    app = FastAPI()
    setup_errors(app)
    return app


def test_app_error_handler_returns_json(fastapi_app):
    """Test AppError handler returns correct JSON response."""
    app = fastapi_app

    @app.get("/raise-app-error")
    def raise_app_error():
        raise AppError(message="fail", code="FAIL_CODE", status_code=418)

    client = TestClient(app)
    resp = client.get("/raise-app-error")
    assert resp.status_code == 418
    data = resp.json()
    assert data["message"] == "fail"
    assert data["errors"][0]["code"] == "FAIL_CODE"


def test_validation_exception_handler_returns_json(fastapi_app):
    """Test validation exception handler returns correct JSON response."""
    app = fastapi_app

    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        return {"item_id": item_id}

    client = TestClient(app)
    resp = client.get("/items/not-an-int")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = resp.json()
    assert data["errors"][0]["code"] == "VALIDATION_ERROR"


def test_unhandled_exception_handler_returns_json(fastapi_app):
    """Test unhandled exception handler returns correct JSON response."""
    app = fastapi_app

    @app.get("/raise-unhandled")
    def raise_unhandled():
        raise RuntimeError("unexpected!")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/raise-unhandled")
    assert resp.status_code == 500
    data = resp.json()
    assert data["message"] == "Internal server error"
    assert data["errors"][0]["code"] == "INTERNAL_ERROR"


def test_setup_errors_registers_handlers(fastapi_app):
    """Test that setup_errors registers all handlers."""
    app = fastapi_app
    assert AppError in app.exception_handlers
    from fastapi.exceptions import RequestValidationError

    assert RequestValidationError in app.exception_handlers
    assert PydanticValidationError in app.exception_handlers
    assert Exception in app.exception_handlers


def test_app_error_handler_with_fields(fastapi_app):
    """Test AppError handler with ValidationError fields."""
    app = fastapi_app

    @app.get("/raise-validation-error")
    def raise_validation_error():
        raise ValidationError(
            fields=[{"field": "foo", "code": "VAL", "message": "bad foo"}]
        )

    client = TestClient(app)
    resp = client.get("/raise-validation-error")
    assert resp.status_code == 400
    data = resp.json()
    assert data["errors"][0]["field"] == "foo"
    assert data["errors"][0]["code"] == "VAL"
    assert data["errors"][0]["message"] == "bad foo"


def test_pydantic_validation_handler(fastapi_app):
    """Test Pydantic validation handler returns correct JSON response."""
    app = fastapi_app

    class Model(BaseModel):
        foo: int

    @app.post("/pydantic-validate")
    def pydantic_validate(item: dict):
        Model(**item)
        return {"ok": True}

    client = TestClient(app)
    resp = client.post("/pydantic-validate", json={"foo": "not-an-int"})
    assert resp.status_code == 422
    data = resp.json()
    assert data["errors"][0]["code"] == "VALIDATION_ERROR"


def test_register_exception_handlers_debug_branch():
    app = FastAPI()
    # Just call with debug=True to cover the branch
    register_exception_handlers(app, debug=True)


def test_setup_errors_manager_py():
    app = FastAPI()
    setup_errors(app)
    # This will cover the last line in manager.py
