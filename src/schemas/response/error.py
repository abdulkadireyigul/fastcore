"""
Error response schemas.

This module contains schemas used for error responses in the API.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.schemas.metadata import ResponseMetadata
from src.schemas.response.base import BaseResponse


class ErrorInfo(BaseModel):
    """
    Detailed error information.

    Attributes:
        code: Error code identifier
        message: Human-readable error message
        field: Optional field name that caused the error
        details: Optional additional error details
    """

    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(
        default=None, description="Field that caused the error"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )


class ErrorResponse(BaseResponse[None, ResponseMetadata]):
    """
    Schema for error responses.

    Example:
        Response for a validation error:
        {
            "success": false,
            "data": null,
            "metadata": {
                "timestamp": "2025-04-15T10:30:00",
                "version": "1.0"
            },
            "message": "Validation error",
            "errors": [
                {
                    "code": "INVALID_INPUT",
                    "message": "Invalid email format",
                    "field": "email",
                    "details": {"value": "invalid-email"}
                }
            ]
        }
    """

    success: bool = Field(default=False, description="Always false for error responses")
    errors: List[ErrorInfo] = Field(
        default_factory=list, description="List of error details"
    )
