"""
Models package for the application.

This package contains all database models used in the application,
organized by domain or feature.
"""

from fastcore.models.security import Permission, Role

__all__ = ["Permission", "Role"]
