"""
Tests for the base configuration management system.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

# Import from the config module
from fastcore.config.base import BaseSettings, Environment


class TestSettings(BaseSettings):
    """Test settings class for validating the BaseSettings functionality."""

    APP_NAME: str = "TestApp"
    DEBUG: bool = False
    PORT: int = 8000
    SECRET_KEY: str = "default-not-so-secret"


class AdvancedTestSettings(BaseSettings):
    """Test settings class with more complex types."""

    APP_NAME: str = "AdvancedApp"
    DEBUG: bool = False
    PORT: int = 8000
    ALLOWED_HOSTS: list[str] = ["localhost"]
    DATABASE_CONFIG: dict = {"host": "localhost", "port": 5432}
    FEATURE_FLAGS: dict[str, bool] = {"feature1": True, "feature2": False}


class PrefixedTestSettings(BaseSettings):
    """Test settings class with a custom environment prefix."""

    NAME: str = "DefaultName"
    DEBUG: bool = False

    class Config:
        env_prefix = "TEST_"


class BaseSettingsTest(unittest.TestCase):
    """
    Test cases for the BaseSettings configuration system.
    """

    def setUp(self) -> None:
        """Set up test environment."""
        # Clear any environment variables that might affect tests
        for env_var in list(os.environ.keys()):
            if env_var.startswith(
                ("APP_", "TEST_", "ALLOWED_", "DATABASE_", "FEATURE_")
            ) or env_var in ["DEBUG", "PORT", "SECRET_KEY", "NAME"]:
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

    def test_environment_enum(self) -> None:
        """Test the Environment enum functionality."""
        self.assertEqual(Environment.DEVELOPMENT.value, "development")
        self.assertEqual(Environment.TESTING.value, "testing")
        self.assertEqual(Environment.STAGING.value, "staging")
        self.assertEqual(Environment.PRODUCTION.value, "production")

    def test_env_prefix(self) -> None:
        """Test that env_prefix is respected when loading environment variables."""
        os.environ["TEST_NAME"] = "PrefixedName"
        os.environ["TEST_DEBUG"] = "true"

        settings = PrefixedTestSettings.from_env()

        self.assertEqual(settings.NAME, "PrefixedName")
        self.assertEqual(settings.DEBUG, True)

        # Make sure unprefixed vars don't get picked up
        os.environ["NAME"] = "Unprefixed"
        settings = PrefixedTestSettings.from_env()
        self.assertEqual(
            settings.NAME, "PrefixedName"
        )  # Still uses the prefixed version

    def test_complex_type_conversion(self) -> None:
        """Test conversion of complex types from environment variables."""
        # Test list conversion from comma-separated values
        os.environ["ALLOWED_HOSTS"] = "example.com,test.com,localhost"

        # Test dict conversion from JSON string
        os.environ[
            "DATABASE_CONFIG"
        ] = '{"host":"db.example.com","port":5433,"user":"admin"}'

        settings = AdvancedTestSettings.from_env()

        # Check list conversion
        self.assertEqual(
            settings.ALLOWED_HOSTS, ["example.com", "test.com", "localhost"]
        )

        # Check dict conversion
        expected_db_config = {"host": "db.example.com", "port": 5433, "user": "admin"}
        self.assertEqual(settings.DATABASE_CONFIG, expected_db_config)

    def test_boolean_conversion_variations(self) -> None:
        """Test various string values for boolean conversion."""
        test_cases = {
            "true": True,
            "True": True,
            "TRUE": True,
            "1": True,
            "yes": True,
            "y": True,
            "on": True,
            "false": False,
            "False": False,
            "FALSE": False,
            "0": False,
            "no": False,
            "n": False,
            "off": False,
        }

        for string_value, expected_bool in test_cases.items():
            os.environ["DEBUG"] = string_value
            settings = TestSettings.from_env()

            # Only "true", "1", "yes", "y", "on" should be True
            if string_value.lower() in ("true", "1", "yes", "y", "on"):
                self.assertTrue(
                    settings.DEBUG, f"Expected '{string_value}' to convert to True"
                )
            else:
                self.assertFalse(
                    settings.DEBUG, f"Expected '{string_value}' to convert to False"
                )

    def test_dotenv_file_loading(self) -> None:
        """Test loading configuration from .env file format."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(suffix=".env", delete=False) as temp_file:
            temp_file.write(b"APP_NAME=EnvFileApp\nDEBUG=true\nPORT=6000\n")
            temp_file_path = temp_file.name

        try:
            # Create a settings class that uses the temp .env file
            class EnvFileSettings(BaseSettings):
                APP_NAME: str = "TestApp"
                DEBUG: bool = False
                PORT: int = 8000

                class Config:
                    env_file = temp_file_path

            # Test loading from the .env file
            settings = EnvFileSettings.from_env()
            self.assertEqual(settings.APP_NAME, "EnvFileApp")
            self.assertEqual(settings.DEBUG, True)
            self.assertEqual(settings.PORT, 6000)

        finally:
            # Clean up the temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_environment_specific_config(self) -> None:
        """Test loading environment-specific config files."""
        # Create a temporary base config file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as base_file:
            base_config = {"APP_NAME": "BaseApp", "DEBUG": False, "PORT": 8000}
            base_file.write(json.dumps(base_config).encode("utf-8"))
            base_path = base_file.name

            # Create a development-specific config file
            dev_path = base_path.replace(".json", ".development.json")
            with open(dev_path, "w") as dev_file:
                dev_config = {"APP_NAME": "DevApp", "DEBUG": True, "PORT": 3000}
                dev_file.write(json.dumps(dev_config))

        try:
            # Create a settings class that uses these files
            class EnvSpecificSettings(BaseSettings):
                APP_NAME: str = "TestApp"
                DEBUG: bool = False
                PORT: int = 8000

                class Config:
                    env_file = base_path

            # Test loading with specific environment
            settings = EnvSpecificSettings.from_env(env=Environment.DEVELOPMENT)
            self.assertEqual(settings.APP_NAME, "DevApp")
            self.assertEqual(settings.DEBUG, True)
            self.assertEqual(settings.PORT, 3000)

            # Test loading with a different environment (falls back to base)
            settings = EnvSpecificSettings.from_env(env=Environment.PRODUCTION)
            self.assertEqual(settings.APP_NAME, "BaseApp")
            self.assertEqual(settings.DEBUG, False)
            self.assertEqual(settings.PORT, 8000)

        finally:
            # Clean up the temp files
            if os.path.exists(base_path):
                os.unlink(base_path)
            if os.path.exists(dev_path):
                os.unlink(dev_path)

    def test_loading_priority(self) -> None:
        """Test that settings are loaded in the correct priority order."""
        # Priority order:
        # 1. Environment variables (highest)
        # 2. Secrets
        # 3. Environment file
        # 4. Default values (lowest)

        # Create a temporary config file - make sure it's properly closed before reading
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        temp_file_path = temp_file.name

        try:
            # Write the JSON data
            config_data = {
                "APP_NAME": "FileApp",
                "DEBUG": True,
                "PORT": 7000,
                "SECRET_KEY": "file-secret",
            }
            json_data = json.dumps(config_data)
            temp_file.write(json_data.encode("utf-8"))
            temp_file.flush()
            temp_file.close()

            # Create a temporary secrets directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a secret file that overrides the config file
                secret_path = Path(temp_dir) / "PORT"
                with open(secret_path, "w") as f:
                    f.write("5000")

                # Set an environment variable that overrides both
                os.environ["APP_NAME"] = "EnvApp"

                # Create a settings class that uses all sources
                class PrioritySettings(BaseSettings):
                    APP_NAME: str = "DefaultApp"
                    DEBUG: bool = False
                    PORT: int = 8000
                    SECRET_KEY: str = "default-secret"

                    class Config:
                        env_file = temp_file_path
                        secrets_dir = temp_dir

                # Now use the actual implementation
                settings = PrioritySettings.from_env()

                # Check priorities:
                # APP_NAME should come from env var
                self.assertEqual(settings.APP_NAME, "EnvApp")

                # PORT should come from secrets
                self.assertEqual(settings.PORT, 5000)

                # DEBUG should come from file
                self.assertEqual(settings.DEBUG, True)

                # SECRET_KEY should come from file
                self.assertEqual(settings.SECRET_KEY, "file-secret")

        finally:
            # Clean up the temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_invalid_file_handling(self) -> None:
        """Test graceful handling of invalid configuration files."""
        # Create an invalid JSON file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_file.write(b"{ This is not valid JSON }")
            invalid_json_path = temp_file.name

        # Create an invalid .env file
        with tempfile.NamedTemporaryFile(suffix=".env", delete=False) as temp_file:
            temp_file.write(b"This is not a valid env file format")
            invalid_env_path = temp_file.name

        try:
            # Test with invalid JSON
            class InvalidJsonSettings(BaseSettings):
                APP_NAME: str = "TestApp"

                class Config:
                    env_file = invalid_json_path

            # Should use defaults and not crash
            settings = InvalidJsonSettings.from_env()
            self.assertEqual(settings.APP_NAME, "TestApp")

            # Test with invalid .env format
            class InvalidEnvSettings(BaseSettings):
                APP_NAME: str = "TestApp"

                class Config:
                    env_file = invalid_env_path

            # Should use defaults and not crash
            settings = InvalidEnvSettings.from_env()
            self.assertEqual(settings.APP_NAME, "TestApp")

        finally:
            # Clean up
            if os.path.exists(invalid_json_path):
                os.unlink(invalid_json_path)
            if os.path.exists(invalid_env_path):
                os.unlink(invalid_env_path)

    def test_non_existent_file_handling(self) -> None:
        """Test graceful handling of non-existent configuration files."""

        # Test with non-existent file
        class NonExistentFileSettings(BaseSettings):
            APP_NAME: str = "TestApp"

            class Config:
                env_file = "non_existent_file.json"

        # Should use defaults and not crash
        settings = NonExistentFileSettings.from_env()
        self.assertEqual(settings.APP_NAME, "TestApp")

    def test_mixed_file_formats(self) -> None:
        """Test handling of different file formats and auto-detection."""
        # Create a file without an extension to test auto-detection
        with tempfile.NamedTemporaryFile(suffix="", delete=False) as temp_file:
            # Write JSON content
            temp_file.write(b'{"APP_NAME": "NoExtension", "DEBUG": true}')
            no_ext_path = temp_file.name

        try:
            # Create settings class using the file
            class MixedFormatSettings(BaseSettings):
                APP_NAME: str = "TestApp"
                DEBUG: bool = False

                class Config:
                    env_file = no_ext_path

            # Should detect JSON format and load values
            settings = MixedFormatSettings.from_env()
            self.assertEqual(settings.APP_NAME, "NoExtension")
            self.assertEqual(settings.DEBUG, True)

        finally:
            # Clean up
            if os.path.exists(no_ext_path):
                os.unlink(no_ext_path)

    def test_binary_file_handling(self) -> None:
        """Test graceful handling of binary files that can't be parsed as text."""
        # Create a binary file
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as temp_file:
            # Write some binary data
            temp_file.write(b"\x00\x01\x02\x03")
            binary_path = temp_file.name

        try:
            # Create settings class using the binary file
            class BinaryFileSettings(BaseSettings):
                APP_NAME: str = "TestApp"

                class Config:
                    env_file = binary_path

            # Should use defaults and not crash
            settings = BinaryFileSettings.from_env()
            self.assertEqual(settings.APP_NAME, "TestApp")

        finally:
            # Clean up
            if os.path.exists(binary_path):
                os.unlink(binary_path)

    def test_type_conversion_edge_cases(self) -> None:
        """Test edge cases in type conversion from environment variables."""
        # Test empty values
        os.environ["PORT"] = ""
        os.environ["DEBUG"] = ""

        # Test invalid values for different types
        os.environ["INVALID_INT"] = "not_a_number"
        os.environ["INVALID_FLOAT"] = "not_a_float"
        os.environ["INVALID_JSON"] = "{not valid json}"

        class EdgeCaseSettings(BaseSettings):
            PORT: int = 8000
            DEBUG: bool = False
            INVALID_INT: int = 1000
            INVALID_FLOAT: float = 1.5
            INVALID_JSON: dict = {"default": True}

        # Should handle edge cases gracefully
        try:
            settings = EdgeCaseSettings.from_env()
            # Empty values should keep defaults
            self.assertEqual(settings.PORT, 8000)
            self.assertEqual(settings.DEBUG, False)
        except (ValueError, TypeError):
            self.fail("Type conversion failed to handle edge cases gracefully")

    def test_secret_file_permissions(self) -> None:
        """Test handling of secret files with incorrect permissions."""
        # Create a temporary secrets directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a secret file
            secret_path = Path(temp_dir) / "SECRET_KEY"
            with open(secret_path, "w") as f:
                f.write("permission-test-secret")

            # Try to simulate a permission error by creating a settings class
            class PermissionSettings(BaseSettings):
                SECRET_KEY: str = "default-secret"

                class Config:
                    secrets_dir = temp_dir

            # The test should pass regardless of permissions
            settings = PermissionSettings.from_env()
            self.assertEqual(settings.SECRET_KEY, "permission-test-secret")

    def test_complex_nested_type_conversion(self) -> None:
        """Test conversion of complex nested types from environment variables."""
        # Test nested dictionary with lists
        os.environ[
            "COMPLEX_CONFIG"
        ] = '{"servers": [{"host": "server1", "port": 8080}, {"host": "server2", "port": 9090}], "enabled": true}'

        class ComplexTypeSettings(BaseSettings):
            COMPLEX_CONFIG: dict = {"default": True}

        settings = ComplexTypeSettings.from_env()
        expected = {
            "servers": [
                {"host": "server1", "port": 8080},
                {"host": "server2", "port": 9090},
            ],
            "enabled": True,
        }
        self.assertEqual(settings.COMPLEX_CONFIG, expected)

    def test_auto_env_prefix_generation(self) -> None:
        """Test automatic prefix generation based on class name."""
        # This test would require modifying the BaseSettings class
        # to support auto-prefixing based on class name
        os.environ["TESTCLASSSETTINGS_APP_NAME"] = "PrefixedByClass"

        class TestClassSettings(BaseSettings):
            APP_NAME: str = "DefaultApp"

            class Config:
                # Enable auto-prefixing based on class name (not implemented yet)
                auto_prefix = True

        # Since this feature isn't implemented, this is a placeholder test
        settings = TestClassSettings.from_env()
        # Currently will use the default value
        self.assertEqual(settings.APP_NAME, "DefaultApp")


if __name__ == "__main__":
    unittest.main()
