from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.base import BaseAppSettings
from src.logging.manager import Logger


def add_cors_middleware(app: FastAPI, settings: BaseAppSettings, logger: Logger):
    """
    Adds CORS middleware to the application. Options are loaded from config.
    """
    cors_options = getattr(
        settings,
        "MIDDLEWARE_CORS_OPTIONS",
        {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        },
    )
    logger.info(f"Configuring CORS middleware with options: {cors_options}")
    app.add_middleware(CORSMiddleware, **cors_options)
    logger.debug("CORS middleware added to FastAPI application.")
