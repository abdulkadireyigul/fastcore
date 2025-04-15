"""
Base metadata schemas for API responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class BaseMetadata(BaseModel):
    """
    Base metadata model defining common fields.

    Attributes:
        timestamp: ISO formatted UTC timestamp
        version: API version string
    """

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of when the response was created",
    )
    version: str = Field(default="1.0", description="API version")


class ResponseMetadata(BaseMetadata):
    """Standard response metadata that can be extended for specific needs."""

    pass
