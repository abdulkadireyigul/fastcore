"""
Error response schemas.

This module contains schemas used for error responses in the API.

Limitations:
- Envelope structure is fixed; customization requires subclassing or code changes
- Only basic metadata (timestamp, version) is included by default
- No built-in support for localization or advanced metadata
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from fastcore.schemas.metadata import ResponseMetadata
from fastcore.schemas.response.base import BaseResponse


class ErrorInfo(BaseModel):
    """
    Detailed error information.

    Features:
    - Includes code, message, field, and details for error reporting

    Limitations:
    - Only basic error details are included by default
    - No built-in support for localization or advanced metadata

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

    Features:
    - Standardized envelope for error responses
    - Includes errors list and standard metadata

    Limitations:
    - Envelope structure is fixed; customization requires subclassing or code changes
    - Only basic metadata (timestamp, version) is included by default
    - No built-in support for localization or advanced metadata

    Attributes:
        errors: List of error details (ErrorInfo)
        metadata: Standard response metadata
        success: Always false for error responses
        message: Error message
    """

    success: bool = Field(default=False, description="Always false for error responses")
    errors: List[ErrorInfo] = Field(
        default_factory=list, description="List of error details"
    )
