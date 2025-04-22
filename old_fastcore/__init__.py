"""
FastCore - A core library for FastAPI applications

This library provides reusable components for FastAPI applications
including configuration management, database connectivity, caching,
and more.
"""

__version__ = "0.1.0"

# API utilities
from fastcore.api.filtering import FilterCondition, FilterOperator, FilterParams
from fastcore.api.pagination import Page, PageInfo, PaginationParams, paginate
from fastcore.api.sorting import SortDirection, SortField, SortParams
from fastcore.config.base import Environment
from fastcore.db.repository import BaseRepository
from fastcore.db.session import Base, Session, get_db
from fastcore.errors.exceptions import AppError

# Expose key components for easier imports
from fastcore.factory import create_app
