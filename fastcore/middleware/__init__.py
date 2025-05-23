"""
Middleware module for FastAPI applications.

Provides centralized setup for common middleware components:
- CORS middleware (configurable via settings)
- Rate limiting middleware (memory or Redis backend)

Limitations:
- Only CORS and rate limiting middleware are included by default
- No request timing middleware is implemented
- No per-route or user-based rate limiting
- Middleware is set up at startup, not dynamically per request
- Advanced CORS and rate limiting features (e.g., per-route config, custom backends) are not included
"""

from .manager import setup_middlewares

__all__ = ["setup_middlewares"]
