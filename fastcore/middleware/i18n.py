"""
Internationalization (i18n) middleware for FastAPI applications.

This module provides middleware for language detection and translation
capabilities in FastAPI applications.
"""

import gettext
import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from fastcore.logging import get_logger

logger = get_logger(__name__)

# Thread-local storage for current language
_thread_local = threading.local()


class I18nConfig(BaseModel):
    """Configuration for internationalization middleware."""

    default_language: str = Field(
        default="en",
        description="Default language code to use when no language is specified",
    )
    supported_languages: List[str] = Field(
        default=["en"], description="List of supported language codes"
    )
    translations_dir: str = Field(
        default="translations", description="Directory containing translation files"
    )
    cookie_name: str = Field(
        default="language",
        description="Name of the cookie to store the user's language preference",
    )
    header_name: str = Field(
        default="Accept-Language",
        description="Name of the header to check for language preference",
    )
    query_param_name: str = Field(
        default="lang",
        description="Name of the query parameter to check for language preference",
    )


class TranslationManager:
    """
    Manager for handling translations across multiple languages.

    This class handles loading and caching translations for different
    languages and provides a simple API for translating messages.
    """

    def __init__(
        self,
        translations_dir: str = "translations",
        default_language: str = "en",
        supported_languages: List[str] = None,
    ):
        """
        Initialize the translation manager.

        Args:
            translations_dir: Directory containing translation files
            default_language: Default language code
            supported_languages: List of supported language codes
        """
        self.translations_dir = Path(translations_dir)
        self.default_language = default_language
        self.supported_languages = supported_languages or [default_language]

        # Dictionary to store translation functions for each language
        self.translations: Dict[str, Any] = {}

        # Dictionary to store translation strings for each language
        self.translation_strings: Dict[str, Dict[str, str]] = {}

        # Load translations
        self._load_translations()

    def _load_translations(self) -> None:
        """
        Load translations for all supported languages.

        Translations can be loaded from gettext .mo files or from
        simple JSON files with key-value pairs.
        """
        for language in self.supported_languages:
            # First try to load from gettext .mo files
            try:
                translation = gettext.translation(
                    "messages",
                    localedir=str(self.translations_dir),
                    languages=[language],
                )
                self.translations[language] = translation.gettext
                logger.debug(f"Loaded gettext translations for {language}")
                continue
            except (FileNotFoundError, OSError):
                pass

            # If gettext fails, try loading from JSON
            json_path = self.translations_dir / f"{language}.json"
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        strings = json.load(f)
                    self.translation_strings[language] = strings
                    logger.debug(f"Loaded JSON translations for {language}")
                    continue
                except (json.JSONDecodeError, OSError) as e:
                    logger.error(f"Error loading JSON translations for {language}: {e}")

            # If no translations are found, use identity function
            if language not in self.translations:
                logger.warning(f"No translations found for {language}")
                self.translations[language] = lambda x: x

    def translate(self, message: str, language: Optional[str] = None) -> str:
        """
        Translate a message to the specified language.

        Args:
            message: The message to translate
            language: The language code to translate to

        Returns:
            The translated message
        """
        # Use provided language or fall back to default
        language = language or self.default_language

        # If language not supported, use default
        if language not in self.supported_languages:
            language = self.default_language

        # If we have a gettext translation function, use it
        if language in self.translations:
            return self.translations[language](message)

        # If we have JSON translations, use them
        if language in self.translation_strings:
            return self.translation_strings[language].get(message, message)

        # Fall back to the original message
        return message


class I18nMiddleware(BaseHTTPMiddleware):
    """
    Middleware for internationalization support in FastAPI applications.

    This middleware detects the user's preferred language from various
    sources (query parameters, headers, cookies) and makes it available
    throughout the request lifecycle.
    """

    def __init__(
        self,
        app: ASGIApp,
        default_language: str = "en",
        supported_languages: List[str] = None,
        translations_dir: str = "translations",
        cookie_name: str = "language",
        header_name: str = "Accept-Language",
        query_param_name: str = "lang",
    ):
        """
        Initialize the i18n middleware.

        Args:
            app: The ASGI application
            default_language: Default language code
            supported_languages: List of supported language codes
            translations_dir: Directory containing translation files
            cookie_name: Name of the cookie to store language preference
            header_name: Name of the header to check for language preference
            query_param_name: Name of the query parameter for language
        """
        super().__init__(app)
        self.default_language = default_language
        self.supported_languages = supported_languages or [default_language]
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.query_param_name = query_param_name

        # Initialize translation manager
        self.translation_manager = TranslationManager(
            translations_dir=translations_dir,
            default_language=default_language,
            supported_languages=self.supported_languages,
        )

        logger.info(
            f"I18n middleware initialized with default language {default_language} "
            f"and supported languages {', '.join(self.supported_languages)}"
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request with language detection.

        Args:
            request: The FastAPI request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next handler
        """
        # Detect the language from various sources
        language = self._detect_language(request)

        # Store the language in the request state for later access
        request.state.language = language

        # Set up the thread-local language for the translator
        previous_language = getattr(_thread_local, "language", None)
        _thread_local.language = language

        # Also update the global translate function to use our translation manager
        global translate
        old_translate = translate
        translate = lambda text, lang=None: self.translation_manager.translate(
            text, lang or language
        )

        try:
            # Process the request
            response = await call_next(request)

            # Set a language cookie if not present
            if self.cookie_name and self.cookie_name not in request.cookies:
                response.set_cookie(
                    key=self.cookie_name, value=language, httponly=True, samesite="lax"
                )

            return response
        finally:
            # Restore the previous language
            if previous_language is not None:
                _thread_local.language = previous_language
            else:
                delattr(_thread_local, "language")

            # Restore the original translate function
            translate = old_translate

    def _detect_language(self, request: Request) -> str:
        """
        Detect the preferred language from the request.

        This method checks for language preferences in the following order:
        1. Query parameter
        2. Cookie
        3. Accept-Language header
        4. Default language

        Args:
            request: The FastAPI request

        Returns:
            The detected language code
        """
        # Check query parameter first
        if self.query_param_name and self.query_param_name in request.query_params:
            lang = request.query_params[self.query_param_name]
            if lang in self.supported_languages:
                return lang

        # Check cookie second
        if self.cookie_name and self.cookie_name in request.cookies:
            lang = request.cookies[self.cookie_name]
            if lang in self.supported_languages:
                return lang

        # Check Accept-Language header third
        if self.header_name and self.header_name in request.headers:
            # Parse Accept-Language header (e.g. "en-US,en;q=0.9,es;q=0.8")
            header = request.headers[self.header_name]
            langs = [lang.split(";")[0].strip() for lang in header.split(",")]

            # Check for exact matches
            for lang in langs:
                if lang in self.supported_languages:
                    return lang

            # Check for language code matches (e.g. "en-US" -> "en")
            for lang in langs:
                code = lang.split("-")[0]
                if code in self.supported_languages:
                    return code

        # Fall back to default language
        return self.default_language


# Functions to access current language and translation


def get_language() -> str:
    """
    Get the current language for the request.

    Returns:
        The current language code
    """
    return getattr(_thread_local, "language", "en")


def translate(message: str, language: Optional[str] = None) -> str:
    """
    Translate a message to the current or specified language.

    This is a placeholder function. The actual translation function
    should be set by the middleware or provided by a dependency injection.

    Args:
        message: The message to translate
        language: Optional language code, defaults to current language

    Returns:
        The translated message
    """
    # This function will be replaced by the actual translation function
    # provided by the middleware
    return message


def configure_i18n(
    app: FastAPI,
    config: Optional[I18nConfig] = None,
    translation_manager: Optional[TranslationManager] = None,
    **kwargs,
) -> None:
    """
    Configure internationalization middleware for a FastAPI application.

    Args:
        app: The FastAPI application instance
        config: An I18nConfig instance with i18n settings
        translation_manager: Optional custom translation manager
        **kwargs: Additional i18n settings to override config values

    Example:
        ```python
        from fastapi import FastAPI
        from fastcore.middleware import configure_i18n, I18nConfig

        app = FastAPI()

        # Using default settings
        configure_i18n(app)

        # Or with custom configuration
        i18n_config = I18nConfig(
            default_language="en",
            supported_languages=["en", "es", "fr"],
            translations_dir="app/translations"
        )
        configure_i18n(app, i18n_config)

        # Or with direct keyword arguments
        configure_i18n(
            app,
            default_language="es",
            supported_languages=["en", "es"]
        )
        ```
    """
    # Create default config if none provided
    if config is None:
        config = I18nConfig()

    # Get configuration parameters
    params = config.dict() if hasattr(config, "dict") else config.model_dump()
    params.update({k: v for k, v in kwargs.items() if v is not None})

    # Create or use provided translation manager
    if not translation_manager:
        translation_manager = TranslationManager(
            translations_dir=params["translations_dir"],
            default_language=params["default_language"],
            supported_languages=params["supported_languages"],
        )

    # Add the i18n middleware
    app.add_middleware(I18nMiddleware, **params)

    # Replace the global translate function with the translation manager's
    global translate
    translate = translation_manager.translate
