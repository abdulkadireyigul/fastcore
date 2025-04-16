"""
CORS (Cross-Origin Resource Sharing) middleware configuration.

This module provides utilities for configuring CORS in FastAPI applications,
allowing controlled access from different origins.
"""

from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class CORSConfig(BaseModel):
    """Configuration model for CORS settings."""

    allow_origins: Union[List[str], List[Union[str, bool]]] = Field(
        default=["*"],
        description="List of allowed origins. Use ['*'] to allow all origins.",
    )
    allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="List of allowed HTTP methods.",
    )
    allow_headers: List[str] = Field(
        default=["*"],
        description="List of allowed HTTP headers. Use ['*'] to allow all headers.",
    )
    allow_credentials: bool = Field(
        default=False,
        description="Whether to allow credentials (cookies, authorization headers).",
    )
    expose_headers: List[str] = Field(
        default=[], description="List of headers that browsers are allowed to access."
    )
    max_age: int = Field(
        default=600, description="Maximum time (in seconds) the results can be cached."
    )

    class Config:
        """Pydantic config for CORSConfig."""

        extra = "forbid"


def configure_cors(app: FastAPI, config: Optional[CORSConfig] = None, **kwargs) -> None:
    """
    Configure CORS middleware for a FastAPI application.

    Args:
        app: The FastAPI application instance
        config: A CORSConfig instance with CORS settings
        **kwargs: Additional CORS settings to override config values

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.middleware import configure_cors, CORSConfig

        app = FastAPI()

        # Using default settings
        configure_cors(app)

        # Or with custom configuration
        cors_config = CORSConfig(
            allow_origins=["https://example.com", "https://api.example.com"],
            allow_credentials=True
        )
        configure_cors(app, cors_config)

        # Or with direct keyword arguments
        configure_cors(app, allow_origins=["https://example.com"], allow_credentials=True)
        ```
    """
    # Create default config if none provided
    if config is None:
        config = CORSConfig()

    # Handle both Pydantic v1 and v2 serialization methods
    if hasattr(config, "model_dump"):
        config_dict = config.model_dump()
    else:
        config_dict = config.dict()

    config_dict.update({k: v for k, v in kwargs.items() if v is not None})

    # Add the CORS middleware to the application
    app.add_middleware(CORSMiddleware, **config_dict)
