"""
Unit tests for the schemas module (metadata, response models).

Covers:
- Instantiation, defaults, and validation for all Pydantic models in schemas/metadata.py and schemas/response/
- Serialization to dict/JSON
- Edge cases for required/optional fields and invalid types
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.schemas.metadata import BaseMetadata, ResponseMetadata
from src.schemas.response.base import BaseResponse
from src.schemas.response.data import DataResponse
from src.schemas.response.error import ErrorInfo, ErrorResponse
from src.schemas.response.list import ListMetadata, ListResponse
from src.schemas.response.token import TokenResponse


# --- BaseMetadata and ResponseMetadata ---
def test_base_metadata_defaults():
    """Test default values and types for BaseMetadata."""
    meta = BaseMetadata()
    assert isinstance(meta.timestamp, datetime)
    assert meta.version == "1.0"


def test_response_metadata_inherits_base():
    """Test ResponseMetadata inherits from BaseMetadata."""
    meta = ResponseMetadata()
    assert isinstance(meta, BaseMetadata)


# --- BaseResponse ---
def test_base_response_instantiation():
    """Test instantiation and field assignment for BaseResponse."""
    meta = ResponseMetadata()
    resp = BaseResponse(success=True, data={"foo": "bar"}, metadata=meta, message="ok")
    assert resp.success is True
    assert resp.data == {"foo": "bar"}
    assert resp.metadata == meta
    assert resp.message == "ok"


# --- DataResponse ---
def test_data_response_required_fields():
    """Test DataResponse requires data and metadata fields."""
    meta = ResponseMetadata()
    resp = DataResponse(data={"id": 1}, metadata=meta)
    assert resp.data == {"id": 1}
    assert isinstance(resp.metadata, ResponseMetadata)


def test_data_response_missing_data_raises():
    """Test DataResponse raises ValidationError if data is missing."""
    meta = ResponseMetadata()
    with pytest.raises(ValidationError):
        DataResponse(metadata=meta)


# --- ErrorInfo and ErrorResponse ---
def test_error_info_fields():
    """Test ErrorInfo field assignment and types."""
    err = ErrorInfo(code="ERR", message="fail", field="foo", details={"x": 1})
    assert err.code == "ERR"
    assert err.message == "fail"
    assert err.field == "foo"
    assert err.details == {"x": 1}


def test_error_response_structure():
    """Test ErrorResponse structure and error list assignment."""
    meta = ResponseMetadata()
    errors = [ErrorInfo(code="E", message="bad", field="f")]
    resp = ErrorResponse(
        success=False, data=None, metadata=meta, errors=errors, message="fail"
    )
    assert resp.success is False
    assert resp.errors == errors
    assert resp.message == "fail"


# --- ListMetadata and ListResponse ---
def test_list_metadata_defaults():
    """Test default values for ListMetadata pagination fields."""
    meta = ListMetadata()
    assert meta.total == 0
    assert meta.page is None
    assert meta.page_size is None
    assert meta.has_next is None
    assert meta.has_previous is None


def test_list_response_with_items():
    """Test ListResponse with a list of items and custom metadata."""
    meta = ListMetadata(
        total=2, page=1, page_size=2, has_next=False, has_previous=False
    )
    data = [{"id": 1}, {"id": 2}]
    resp = ListResponse(data=data, metadata=meta)
    assert resp.data == data
    assert resp.metadata == meta


# --- TokenResponse ---
def test_token_response_required_fields():
    """Test TokenResponse required and default fields."""
    resp = TokenResponse(access_token="abc", expires_in=3600)
    assert resp.token_type == "bearer"
    assert resp.access_token == "abc"
    assert resp.expires_in == 3600
    assert resp.refresh_token is None


def test_token_response_missing_access_token_raises():
    """Test TokenResponse raises ValidationError if access_token is missing."""
    with pytest.raises(ValidationError):
        TokenResponse(expires_in=3600)


# --- Serialization ---
def test_error_info_serialization():
    """Test ErrorInfo serialization to dict using model_dump."""
    err = ErrorInfo(code="E", message="bad")
    d = err.model_dump()
    assert d["code"] == "E"
    assert d["message"] == "bad"


def test_data_response_serialization():
    """Test DataResponse serialization to dict using model_dump."""
    meta = ResponseMetadata()
    resp = DataResponse(data={"foo": "bar"}, metadata=meta)
    d = resp.model_dump()
    assert d["data"] == {"foo": "bar"}
    assert "metadata" in d


# --- Edge Cases ---
def test_error_info_extra_fields_ignored():
    """Test ErrorInfo ignores extra fields not defined in the model."""
    err = ErrorInfo(code="E", message="bad", extra="ignored")
    assert not hasattr(err, "extra")


def test_list_response_empty_data():
    """Test ListResponse with empty data list."""
    meta = ListMetadata()
    resp = ListResponse(data=[], metadata=meta)
    assert resp.data == []
    assert resp.metadata == meta
