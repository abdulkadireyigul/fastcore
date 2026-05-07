"""
UUID Database Module Exports.

Exposes the UUIDBaseModel and GUID type for use in application models.
Usage:
    from fastcore.db.uuid import UUIDBaseModel, GUID
"""

from .base import GUID, UUIDBaseModel

__all__ = ["UUIDBaseModel", "GUID"]
