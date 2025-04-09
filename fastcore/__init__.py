"""
FastCore - A core library for FastAPI applications

This library provides reusable components for FastAPI applications
including configuration management, database connectivity, caching,
and more.
"""

__version__ = "0.1.0"

# Expose key components for easier imports
from fastcore.app_factory import create_app
from fastcore.config.base import Environment
from fastcore.db.session import get_db, Session, Base
from fastcore.db.repository import BaseRepository
from fastcore.errors.exceptions import AppException
