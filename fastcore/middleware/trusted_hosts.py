"""
Trusted hosts middleware for FastAPI applications.

This module provides middleware for validating that requests are coming
from trusted host domains, helping to prevent Host header attacks.
"""

import re
from typing import List, Optional, Pattern, Union

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, validator
from starlette.datastructures import URL, Headers
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp

from fastcore.logging import get_logger

logger = get_logger(__name__)


class TrustedHostsConfig(BaseModel):
    """Configuration for trusted hosts middleware."""

    allowed_hosts: List[str] = Field(
        default=["*"],
        description="List of allowed hosts. Use ['*'] to allow all hosts.",
    )
    www_redirect: bool = Field(
        default=True,
        description="Whether to redirect from 'www.example.com' to 'example.com'.",
    )
    https_redirect: bool = Field(
        default=False, description="Whether to redirect from 'http://' to 'https://'."
    )

    @validator("allowed_hosts", allow_reuse=True)
    def validate_allowed_hosts(cls, hosts):
        """Validate the allowed hosts configuration."""
        # Check if wildcard is used correctly
        if "*" in hosts and len(hosts) > 1:
            raise ValueError("If '*' is used, no other hosts should be specified")
        return hosts


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates the Host header in requests.

    This middleware helps protect against HTTP Host header attacks by
    ensuring that requests are only accepted from trusted hosts.
    It can also handle redirections from www to non-www versions
    and from HTTP to HTTPS.
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: List[str] = None,
        www_redirect: bool = True,
        https_redirect: bool = False,
    ):
        """
        Initialize the trusted host middleware.

        Args:
            app: The ASGI application
            allowed_hosts: List of allowed hosts, use ["*"] to allow all hosts
            www_redirect: Whether to redirect www to non-www
            https_redirect: Whether to redirect HTTP to HTTPS
        """
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["*"]
        self.www_redirect = www_redirect
        self.https_redirect = https_redirect
        self.host_patterns = self._compile_patterns(self.allowed_hosts)

        logger.info(
            f"Trusted hosts middleware configured with {len(self.allowed_hosts)} hosts"
        )

    def _compile_patterns(self, hosts: List[str]) -> List[Pattern]:
        """
        Compile regex patterns for host matching.

        Args:
            hosts: List of host patterns

        Returns:
            List of compiled regex patterns
        """
        patterns = []

        if "*" in hosts:
            # Match all hosts if wildcard is specified
            return [re.compile(r".*")]

        for host in hosts:
            # Replace wildcards with regex pattern
            if "*" in host:
                pattern = host.replace(".", r"\.").replace("*", r".*")
            else:
                pattern = re.escape(host)

            # Ensure the pattern matches the entire host
            pattern = f"^{pattern}$"
            patterns.append(re.compile(pattern))

        return patterns

    def _is_host_allowed(self, host: str) -> bool:
        """
        Check if a host is allowed.

        Args:
            host: The host to check

        Returns:
            True if the host is allowed, False otherwise
        """
        return any(pattern.match(host) for pattern in self.host_patterns)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request with host validation.

        Args:
            request: The FastAPI request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next handler or an error response
        """
        # Get the host from the request
        host = request.headers.get("host", "").split(":")[0]

        # Check if the host is allowed
        if not self._is_host_allowed(host):
            logger.warning(f"Request from disallowed host: {host}")
            return PlainTextResponse("Invalid host header", status_code=400)

        # Handle www redirects if enabled
        if self.www_redirect and host.startswith("www."):
            base_host = host[4:]  # Remove 'www.'

            # Check if the base domain is allowed
            if self._is_host_allowed(base_host):
                url = URL(str(request.url))
                redirect_url = url.replace(netloc=base_host)

                logger.debug(f"Redirecting from {host} to {base_host}")
                return Response(
                    status_code=301, headers={"location": str(redirect_url)}
                )

        # Handle HTTPS redirects if enabled
        if (
            self.https_redirect
            and request.url.scheme == "http"
            and not request.headers.get("x-forwarded-proto") == "https"
        ):
            url = URL(str(request.url))
            redirect_url = url.replace(scheme="https")

            logger.debug(f"Redirecting from HTTP to HTTPS")
            return Response(status_code=301, headers={"location": str(redirect_url)})

        # Process the request normally
        return await call_next(request)


def configure_trusted_hosts(
    app: FastAPI, config: Optional[TrustedHostsConfig] = None, **kwargs
) -> None:
    """
    Configure trusted hosts middleware for a FastAPI application.

    Args:
        app: The FastAPI application instance
        config: A TrustedHostsConfig instance with settings
        **kwargs: Additional settings to override config values

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.middleware import configure_trusted_hosts, TrustedHostsConfig

        app = FastAPI()

        # Using default settings (allow all hosts)
        configure_trusted_hosts(app)

        # Or with custom configuration
        hosts_config = TrustedHostsConfig(
            allowed_hosts=["example.com", "api.example.com"],
            www_redirect=True,
            https_redirect=True
        )
        configure_trusted_hosts(app, hosts_config)

        # Or with direct keyword arguments
        configure_trusted_hosts(
            app,
            allowed_hosts=["example.com"],
            https_redirect=True
        )
        ```
    """
    # Create default config if none provided
    if config is None:
        config = TrustedHostsConfig()

    # Get configuration parameters
    params = config.dict() if hasattr(config, "dict") else config.model_dump()
    params.update({k: v for k, v in kwargs.items() if v is not None})

    # Add the trusted hosts middleware
    app.add_middleware(TrustedHostMiddleware, **params)
