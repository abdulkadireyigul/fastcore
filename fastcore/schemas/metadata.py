"""
Base metadata schemas for API responses.

Provides timestamp and version metadata for API responses.

Limitations:
- Only basic metadata (timestamp, version) is included by default
- No built-in support for advanced metadata or localization
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BaseMetadata(BaseModel):
    """
    Base metadata model defining common fields.

    Features:
    - Includes timestamp (UTC) and API version

    Limitations:
    - Only basic metadata (timestamp, version) is included by default
    - No built-in support for advanced metadata or localization
    """

    timestamp: datetime = Field(
        # default_factory=datetime.utcnow,
        default=datetime.now(timezone.utc),
        description="Timestamp of when the response was created",
    )
    version: str = Field(default="1.0", description="API version")


class ResponseMetadata(BaseMetadata):
    """
    Standard response metadata that can be extended for specific needs.

    Limitations:
    - Only basic metadata (timestamp, version) is included by default
    - No built-in support for advanced metadata or localization
    """

    pass
