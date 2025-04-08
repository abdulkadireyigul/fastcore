"""
Tests for the base configuration management system.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

# Import from the config module
from fastcore.config.base import BaseSettings


class TestSettings(BaseSettings):
    """Test settings class for validating the BaseSettings functionality."""

    APP_NAME: str = "TestApp"
    DEBUG: bool = False
    PORT: int = 8000
    SECRET_KEY: str = "default-not-so-secret"


class BaseSettingsTest(unittest.TestCase):
    """
    Test cases for the BaseSettings configuration system.
    """

    def setUp(self) -> None:
        """Set up test environment."""
        # Clear any environment variables that might affect tests
        for env_var in list(os.environ.keys()):
            if env_var.startswith("APP_") or env_var in ["DEBUG", "PORT", "SECRET_KEY"]:
                del os.environ[env_var]

    def test_default_values(self) -> None:
        """Test that default values are used when no overrides exist."""
        settings = TestSettings()
        self.assertEqual(settings.APP_NAME, "TestApp")
        self.assertEqual(settings.DEBUG, False)
        self.assertEqual(settings.PORT, 8000)
        self.assertEqual(settings.SECRET_KEY, "default-not-so-secret")

    def test_env_override(self) -> None:
        """Test that environment variables override defaults."""
        os.environ["APP_NAME"] = "EnvApp"
        os.environ["DEBUG"] = "true"
        os.environ["PORT"] = "9000"

        settings = TestSettings.from_env()

        self.assertEqual(settings.APP_NAME, "EnvApp")
        # Updated to match expected type conversion to boolean
        self.assertEqual(settings.DEBUG, True)
        # Updated to match expected type conversion to integer
        self.assertEqual(settings.PORT, 9000)

    def test_env_file_loading(self) -> None:
        """Test loading configuration from environment file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            config_data = {"APP_NAME": "FileApp", "DEBUG": True, "PORT": 7000}
            temp_file.write(json.dumps(config_data).encode("utf-8"))
            temp_file_path = temp_file.name

        try:
            # Create a settings class that uses the temp file
            class FileSettings(BaseSettings):
                APP_NAME: str = "TestApp"
                DEBUG: bool = False
                PORT: int = 8000

                class Config:
                    env_file = temp_file_path

            # Test loading from the file
            settings = FileSettings.from_env()
            self.assertEqual(settings.APP_NAME, "FileApp")
            self.assertEqual(settings.DEBUG, True)
            self.assertEqual(settings.PORT, 7000)

        finally:
            # Clean up the temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_secrets_loading(self) -> None:
        """Test loading secrets from a secrets directory."""
        # Create a temporary secrets directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a secret file
            secret_path = Path(temp_dir) / "SECRET_KEY"
            with open(secret_path, "w") as f:
                f.write("super-secret-value")

            # Create a settings class that uses the temp secrets dir
            class SecretSettings(BaseSettings):
                APP_NAME: str = "TestApp"
                SECRET_KEY: str = "default-secret"

                class Config:
                    secrets_dir = temp_dir

            # Test loading the secret
            settings = SecretSettings.from_env()
            self.assertEqual(settings.APP_NAME, "TestApp")  # Default value
            self.assertEqual(settings.SECRET_KEY, "super-secret-value")  # From secrets


if __name__ == "__main__":
    unittest.main()
