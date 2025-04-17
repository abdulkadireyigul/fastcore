"""
Middleware manager for environment-specific configurations.

This module provides utilities for configuring middleware components with
sensible defaults based on the current environment.
"""

import logging
from typing import List, Optional

from fastapi import FastAPI
from fastcore.middleware.cors import CORSConfig, configure_cors
from fastcore.middleware.i18n import I18nConfig, configure_i18n
from fastcore.middleware.rate_limiting import RateLimitConfig, configure_rate_limiting
from fastcore.middleware.timing import TimingConfig, configure_timing
from fastcore.middleware.trusted_hosts import (
    TrustedHostsConfig,
    configure_trusted_hosts,
)

from fastcore.config.base import Environment
from fastcore.logging import get_logger

# Get a logger for this module
logger = get_logger(__name__)


def get_default_cors_config(env: Environment) -> CORSConfig:
    """
    Get environment-specific default CORS configuration.

    Args:
        env: The current environment

    Returns:
        A CORSConfig with sensible defaults for the environment
    """
    if env == Environment.DEVELOPMENT or env == Environment.TESTING:
        # In development/testing: Allow all origins, methods, and headers
        return CORSConfig(
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )
    else:
        # In production/staging: More restrictive defaults
        # Should be overridden with specific allowed origins
        return CORSConfig(
            allow_origins=[],  # No default origins in production
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=False,
        )


def get_default_rate_limit_config(env: Environment) -> RateLimitConfig:
    """
    Get environment-specific default rate limiting configuration.

    Args:
        env: The current environment

    Returns:
        A RateLimitConfig with sensible defaults for the environment
    """
    if env == Environment.DEVELOPMENT or env == Environment.TESTING:
        # In development/testing: Very generous limits
        return RateLimitConfig(
            enabled=False,  # Disabled by default in development
            limit=1000,
            window_seconds=60,
            exclude_paths=["/docs", "/redoc", "/openapi.json"],
        )
    elif env == Environment.STAGING:
        # In staging: Moderate limits
        return RateLimitConfig(
            enabled=True,
            limit=100,
            window_seconds=60,
            exclude_paths=["/docs", "/redoc", "/openapi.json"],
        )
    else:
        # In production: Stricter limits
        return RateLimitConfig(
            enabled=True,
            limit=60,
            window_seconds=60,
            exclude_paths=["/health"],
        )


def get_default_trusted_hosts_config(env: Environment) -> TrustedHostsConfig:
    """
    Get environment-specific default trusted hosts configuration.

    Args:
        env: The current environment

    Returns:
        A TrustedHostsConfig with sensible defaults for the environment
    """
    if env == Environment.DEVELOPMENT or env == Environment.TESTING:
        # In development/testing: Allow all hosts
        return TrustedHostsConfig(
            enabled=False,
            allowed_hosts=["*"],
        )
    else:
        # In production/staging: No default trusted hosts
        # Should be explicitly configured
        return TrustedHostsConfig(
            enabled=True,
            allowed_hosts=[],  # No default hosts in production
        )


def get_default_timing_config(env: Environment) -> TimingConfig:
    """
    Get environment-specific default request timing configuration.

    Args:
        env: The current environment

    Returns:
        A TimingConfig with sensible defaults for the environment
    """
    if env == Environment.DEVELOPMENT or env == Environment.TESTING:
        # In development/testing: Enable timing for all requests with debug info
        return TimingConfig(
            enabled=True,
            include_in_response=True,
            slow_request_threshold_ms=500,
            log_level=logging.INFO,
        )
    elif env == Environment.STAGING:
        # In staging: Enable timing but only include in logs
        return TimingConfig(
            enabled=True,
            include_in_response=False,
            slow_request_threshold_ms=200,
            log_level=logging.INFO,
        )
    else:
        # In production: Only log slow requests
        return TimingConfig(
            enabled=True,
            include_in_response=False,
            slow_request_threshold_ms=100,
            log_level=logging.WARNING,
        )


def get_default_i18n_config(env: Environment) -> I18nConfig:
    """
    Get environment-specific default i18n configuration.

    Args:
        env: The current environment

    Returns:
        An I18nConfig with sensible defaults for the environment
    """
    # I18n config doesn't change much between environments
    return I18nConfig(
        default_language="en",
        supported_languages=["en"],
        translations_dir="translations",
    )


def configure_environment_middleware(
    app: FastAPI,
    env: Environment,
    cors: Optional[CORSConfig] = None,
    rate_limit: Optional[RateLimitConfig] = None,
    trusted_hosts: Optional[TrustedHostsConfig] = None,
    timing: Optional[TimingConfig] = None,
    i18n: Optional[I18nConfig] = None,
    enable_cors: bool = True,
    enable_rate_limiting: bool = False,
    enable_trusted_hosts: bool = False,
    enable_timing: bool = False,
    enable_i18n: bool = False,
) -> None:
    """
    Configure middleware with environment-specific defaults.

    Args:
        app: The FastAPI application instance
        env: The current environment
        cors: Optional custom CORS configuration
        rate_limit: Optional custom rate limiting configuration
        trusted_hosts: Optional custom trusted hosts configuration
        timing: Optional custom request timing configuration
        i18n: Optional custom internationalization configuration
        enable_cors: Whether to enable CORS middleware
        enable_rate_limiting: Whether to enable rate limiting middleware
        enable_trusted_hosts: Whether to enable trusted hosts middleware
        enable_timing: Whether to enable request timing middleware
        enable_i18n: Whether to enable internationalization middleware

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.config.base import Environment
        from fastcore.middleware.manager import configure_environment_middleware
        from fastcore.middleware import CORSConfig

        app = FastAPI()

        # Configure with environment-specific defaults
        configure_environment_middleware(app, Environment.PRODUCTION)

        # Or with custom overrides
        cors_config = CORSConfig(
            allow_origins=["https://myapp.com"],
            allow_credentials=True
        )
        configure_environment_middleware(
            app,
            Environment.PRODUCTION,
            cors=cors_config,
            enable_rate_limiting=True
        )
        ```
    """
    logger.info(f"Configuring middleware for environment: {env}")

    # Configure middlewares in the correct order

    # 1. Trusted Hosts middleware (should be first)
    if enable_trusted_hosts:
        hosts_config = trusted_hosts or get_default_trusted_hosts_config(env)
        if hosts_config.enabled:
            configure_trusted_hosts(app, hosts_config)
            logger.debug(
                f"Trusted hosts middleware configured with: {hosts_config.allowed_hosts}"
            )

    # 2. CORS middleware
    if enable_cors:
        cors_config = cors or get_default_cors_config(env)
        configure_cors(app, cors_config)
        origins = cors_config.allow_origins
        logger.debug(f"CORS middleware configured with origins: {origins}")

    # 3. Rate limiting middleware
    if enable_rate_limiting:
        rate_config = rate_limit or get_default_rate_limit_config(env)
        if rate_config.enabled:
            configure_rate_limiting(app, rate_config)
            logger.debug(
                f"Rate limiting middleware configured: {rate_config.limit} requests per {rate_config.window_seconds}s"
            )

    # 4. Timing middleware
    if enable_timing:
        time_config = timing or get_default_timing_config(env)
        if time_config.enabled:
            configure_timing(app, time_config)
            logger.debug(
                f"Timing middleware configured, threshold: {time_config.slow_request_threshold_ms}ms"
            )

    # 5. i18n middleware (should be last in the chain)
    if enable_i18n:
        i18n_config = i18n or get_default_i18n_config(env)
        configure_i18n(app, i18n_config)
        logger.debug(
            f"i18n middleware configured with languages: {i18n_config.supported_languages}"
        )
