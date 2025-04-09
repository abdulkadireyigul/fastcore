"""
FastCore Middleware Module.

This module provides middleware components for FastAPI applications, including:
- CORS (Cross-Origin Resource Sharing) configuration
- Rate limiting for API endpoints
- Internationalization (i18n) support
- Trusted hosts validation
- Request timing and metrics collection
"""

from .cors import CORSConfig, configure_cors
from .i18n import I18nConfig, I18nMiddleware, configure_i18n, get_language, translate
from .rate_limiting import RateLimitConfig, RateLimiter, configure_rate_limiting
from .timing import TimingConfig, TimingMiddleware, configure_timing
from .trusted_hosts import (
    TrustedHostMiddleware,
    TrustedHostsConfig,
    configure_trusted_hosts,
)

__all__ = [
    # CORS
    "CORSConfig",
    "configure_cors",
    # Rate limiting
    "RateLimiter",
    "RateLimitConfig",
    "configure_rate_limiting",
    # Internationalization
    "I18nMiddleware",
    "I18nConfig",
    "configure_i18n",
    "get_language",
    "translate",
    # Trusted hosts
    "TrustedHostMiddleware",
    "TrustedHostsConfig",
    "configure_trusted_hosts",
    # Request timing
    "TimingMiddleware",
    "TimingConfig",
    "configure_timing",
]
