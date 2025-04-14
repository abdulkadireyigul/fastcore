"""
Example demonstrating how to use the app factory with middleware components in FastCore.

This example shows how to create a FastAPI application using the app factory
with various middleware components enabled and configured.
"""

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from fastcore.config.base import Environment
from fastcore.factory import create_app
from fastcore.middleware import (
    CORSConfig,
    I18nConfig,
    RateLimitConfig,
    TimingConfig,
    TrustedHostsConfig,
    get_language,
    translate,
)

# Create a FastAPI application with middleware components enabled
app = create_app(
    env=Environment.DEVELOPMENT,
    # Basic settings
    enable_logging=True,
    enable_database=False,
    # Enable middleware components
    enable_cors=True,
    enable_rate_limiting=True,
    enable_i18n=True,
    enable_trusted_hosts=True,
    enable_timing=True,
    # Configure middleware
    cors_config=CORSConfig(
        allow_origins=["http://localhost:3000", "https://example.com"],
        allow_credentials=True,
    ),
    rate_limit_config=RateLimitConfig(
        limit=100,  # 100 requests per minute
        window_seconds=60,
        exclude_paths=["/docs", "/redoc", "/openapi.json", "/health"],
    ),
    i18n_config=I18nConfig(
        default_language="en",
        supported_languages=["en", "es", "fr"],
        translations_dir="translations",
    ),
    trusted_hosts_config=TrustedHostsConfig(
        allowed_hosts=["localhost", "127.0.0.1", "example.com"],
        www_redirect=True,
    ),
    timing_config=TimingConfig(
        header_name="X-Process-Time",
        log_level="info",
        log_threshold_ms=200,  # Only log requests that take longer than 200ms
    ),
)

# Define some example routes to demonstrate middleware functionality


@app.get("/")
async def root():
    """Basic endpoint to test middleware."""
    return {"message": translate("Welcome to FastCore!")}


@app.get("/hello/{name}")
async def hello(name: str, request: Request):
    """
    Greeting endpoint demonstrating i18n middleware.

    Shows how to use the current language and translation functions.
    """
    # Get the detected language from the request state
    language = get_language()

    # Translate the greeting based on language
    greeting = translate("Hello", language)

    return {
        "greeting": f"{greeting}, {name}!",
        "language": language,
    }


@app.get("/protected")
async def protected_route(request: Request):
    """
    Protected endpoint demonstrating rate limiting.

    This endpoint is subject to rate limiting.
    """
    return {
        "message": translate("This is a protected resource"),
        "client_ip": request.client.host,
    }


@app.get("/slow")
async def slow_response():
    """
    Slow endpoint demonstrating timing middleware.

    This endpoint introduces a delay to trigger the timing middleware logging.
    """
    import time

    time.sleep(0.5)  # 500ms delay
    return {"message": translate("This was a slow request")}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app_factory_middleware_example:app", host="0.0.0.0", port=8000, reload=True
    )
