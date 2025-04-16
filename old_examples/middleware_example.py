"""
Example demonstrating how to use middleware components in FastCore.

This example shows how to configure and use the various middleware
components provided by FastCore in a FastAPI application.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fastcore.middleware import (  # CORS middleware; Rate limiting middleware; Internationalization middleware; Trusted hosts middleware; Request timing middleware
    CORSConfig,
    I18nConfig,
    RateLimitConfig,
    TimingConfig,
    TrustedHostsConfig,
    configure_cors,
    configure_i18n,
    configure_rate_limiting,
    configure_timing,
    configure_trusted_hosts,
    get_language,
    translate,
)

# Create a FastAPI application
app = FastAPI(title="FastCore Middleware Example")

# 1. Configure CORS middleware
cors_config = CORSConfig(
    allow_origins=["http://localhost:3000", "https://example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
configure_cors(app, cors_config)

# 2. Configure rate limiting middleware
rate_limit_config = RateLimitConfig(
    limit=100,  # 100 requests per minute
    window_seconds=60,
    exclude_paths=["/docs", "/redoc", "/openapi.json"],
)
configure_rate_limiting(app, rate_limit_config)

# 3. Configure internationalization middleware
i18n_config = I18nConfig(
    default_language="en",
    supported_languages=["en", "es", "fr"],
    translations_dir="translations",
)
configure_i18n(app, i18n_config)

# 4. Configure trusted hosts middleware
trusted_hosts_config = TrustedHostsConfig(
    allowed_hosts=["localhost", "127.0.0.1", "example.com"],
    www_redirect=True,
    https_redirect=False,
)
configure_trusted_hosts(app, trusted_hosts_config)

# 5. Configure timing middleware
timing_config = TimingConfig(
    header_name="X-Process-Time",
    log_level="info",
    log_threshold_ms=200,  # Only log requests that take longer than 200ms
)
configure_timing(app, timing_config)

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

    uvicorn.run("middleware_example:app", host="0.0.0.0", port=8000, reload=True)
