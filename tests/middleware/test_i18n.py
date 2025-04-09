"""
Tests for internationalization (i18n) middleware implementation.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from fastcore.middleware.i18n import (
    I18nConfig,
    I18nMiddleware,
    TranslationManager,
    configure_i18n,
    get_language,
    translate,
)


class TestI18nConfig:
    """Tests for I18nConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = I18nConfig()
        assert config.default_language == "en"
        assert config.supported_languages == ["en"]
        assert config.translations_dir == "translations"
        assert config.cookie_name == "language"
        assert config.header_name == "Accept-Language"
        assert config.query_param_name == "lang"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = I18nConfig(
            default_language="fr",
            supported_languages=["en", "fr", "es"],
            translations_dir="/custom/path",
            cookie_name="locale",
            header_name="X-Language",
            query_param_name="language",
        )
        assert config.default_language == "fr"
        assert config.supported_languages == ["en", "fr", "es"]
        assert config.translations_dir == "/custom/path"
        assert config.cookie_name == "locale"
        assert config.header_name == "X-Language"
        assert config.query_param_name == "language"


class TestTranslationManager:
    """Tests for TranslationManager."""

    @pytest.fixture
    def temp_translations_dir(self):
        """Create a temporary directory for test translations."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Create a test Spanish translation file
            es_path = Path(tmpdirname) / "es.json"
            with open(es_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"Hello": "Hola", "Welcome": "Bienvenido", "Goodbye": "Adiós"}, f
                )

            # Create a test French translation file
            fr_path = Path(tmpdirname) / "fr.json"
            with open(fr_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "Hello": "Bonjour",
                        "Welcome": "Bienvenue",
                        "Goodbye": "Au revoir",
                    },
                    f,
                )

            yield tmpdirname

    def test_load_translations(self, temp_translations_dir):
        """Test loading translations from files."""
        manager = TranslationManager(
            translations_dir=temp_translations_dir,
            default_language="en",
            supported_languages=["en", "es", "fr", "de"],
        )

        # Test translations that exist
        assert manager.translate("Hello", "es") == "Hola"
        assert manager.translate("Welcome", "fr") == "Bienvenue"

        # Test fallback to default for unsupported language
        assert manager.translate("Hello", "de") == "Hello"  # German not available

        # Test unknown key falls back to the original text
        assert manager.translate("Unknown", "es") == "Unknown"

        # Test default language
        assert manager.translate("Hello") == "Hello"  # Default language is English

    def test_translate_with_none_language(self, temp_translations_dir):
        """Test translate with None language falls back to default."""
        manager = TranslationManager(
            translations_dir=temp_translations_dir,
            default_language="es",
            supported_languages=["en", "es"],
        )

        assert manager.translate("Hello", None) == "Hola"


class TestI18nMiddleware:
    """Tests for I18nMiddleware."""

    @pytest.fixture
    def temp_translations_dir(self):
        """Create a temporary directory for test translations."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Create a test Spanish translation file
            es_path = Path(tmpdirname) / "es.json"
            with open(es_path, "w", encoding="utf-8") as f:
                json.dump({"Hello": "Hola", "Welcome": "Bienvenido"}, f)

            # Create a test English translation file to ensure fallback works
            en_path = Path(tmpdirname) / "en.json"
            with open(en_path, "w", encoding="utf-8") as f:
                json.dump({"Hello": "Hello", "Welcome": "Welcome"}, f)

            yield tmpdirname

    @pytest.fixture
    def translation_manager(self, temp_translations_dir):
        """Create a translation manager for tests."""
        return TranslationManager(
            translations_dir=temp_translations_dir,
            default_language="en",
            supported_languages=["en", "es", "fr"],
        )

    @pytest.fixture
    def app(self, temp_translations_dir, translation_manager):
        """Create a test FastAPI app with i18n middleware."""
        app = FastAPI()

        # Define a dependency to access the translations
        def get_translator():
            return translation_manager

        # Add test endpoints that use the translation manager directly
        @app.get("/hello")
        def hello(
            translator: TranslationManager = Depends(get_translator),
            request: Request = None,
        ):
            # Get language from request state if available (set by middleware)
            lang = (
                request.state.language
                if request and hasattr(request.state, "language")
                else None
            )
            return {"message": translator.translate("Hello", lang)}

        # Configure i18n middleware
        app.add_middleware(
            I18nMiddleware,
            default_language="en",
            supported_languages=["en", "es", "fr"],
            translations_dir=temp_translations_dir,
        )

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        # Initialize the client with no cookies
        client = TestClient(app)
        return client

    def test_detect_language_from_query_param(self, client):
        """Test language detection from query parameter."""
        response = client.get("/hello?lang=es")
        assert response.json() == {"message": "Hola"}

        # Check that a cookie was set
        assert "language=es" in response.headers["set-cookie"]

    def test_detect_language_from_cookie(self, client):
        """Test language detection from cookie."""
        # Instead of sending cookies in the request, set them on the client
        client.cookies.set("language", "es")
        response = client.get("/hello")
        assert response.json() == {"message": "Hola"}

    def test_detect_language_from_header(self, client):
        """Test language detection from Accept-Language header."""
        response = client.get("/hello", headers={"Accept-Language": "es"})
        assert response.json() == {"message": "Hola"}

        # Test with complex Accept-Language header
        # The test is expecting French to be used first, but since we don't have French translations,
        # it should use the next supported language from the header which is Spanish in this case,
        # since es has a higher priority (q=0.8) than en (q=0.7)
        response = client.get(
            "/hello", headers={"Accept-Language": "fr-FR,fr;q=0.9,es;q=0.8,en;q=0.7"}
        )
        assert response.json() == {
            "message": "Hola"
        }  # Should use es since fr is not available

        # Test with language code extraction
        response = client.get("/hello", headers={"Accept-Language": "es-ES,es;q=0.9"})
        assert response.json() == {"message": "Hola"}  # Should extract es from es-ES

    def test_fallback_to_default(self, client):
        """Test fallback to default language."""
        # With unsupported language
        response = client.get("/hello?lang=de")
        assert response.json() == {"message": "Hello"}  # Falls back to English

    def test_configure_i18n(self):
        """Test the configure_i18n function."""
        app = FastAPI()

        # With default config
        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_i18n(app)

            # Check that middleware was added
            mock_add_middleware.assert_called_once()

        # With custom config
        mock_add_middleware.reset_mock()
        config = I18nConfig(default_language="fr", supported_languages=["en", "fr"])

        with patch(
            "fastapi.applications.FastAPI.add_middleware"
        ) as mock_add_middleware:
            configure_i18n(app, config)

            # Check that middleware was added
            mock_add_middleware.assert_called_once()

    def test_get_language_function(self):
        """Test the get_language function."""
        # Should return default when not set
        assert get_language() == "en"

        # Can't easily test thread-local in unit tests, but at least check it exists
        assert get_language is not None
