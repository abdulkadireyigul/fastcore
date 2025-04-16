"""
Base configuration system for applications.

A simple, consistent configuration management system that loads settings
from environment variables, files, and secrets directories.
"""

import json
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, get_origin, get_type_hints

T = TypeVar("T", bound="BaseSettings")


class Environment(str, Enum):
    """
    Environment types for configuration loading.

    This enum defines standard environment types used for configuration management.
    Each environment can have different configuration values and behaviors.
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class BaseSettings:
    """
    Base class for application settings.

    Provides methods to load settings from multiple sources in priority order:
    1. Environment variables (highest priority)
    2. Secrets directory (medium priority)
    3. Environment file (lowest priority)
    4. Default values defined in the class

    Example:
        ```python
        class DatabaseSettings(BaseSettings):
            HOST: str = "localhost"
            PORT: int = 5432
            USER: str = "postgres"
            PASSWORD: str

            class Config:
                env_prefix = "DB_"

        # Load settings from environment variables (DB_HOST, DB_PORT, etc.)
        db_settings = DatabaseSettings.from_env()
        print(db_settings.HOST)  # Will use env var DB_HOST if set, otherwise "localhost"
        ```
    """

    class Config:
        """
        Configuration for settings behavior.

        Attributes:
            env_prefix: Prefix to add to environment variable names when looking them up
            env_file: Path to a JSON file containing configuration values
            secrets_dir: Directory containing secret values stored in individual files
        """

        env_prefix: str = ""
        env_file: Optional[str] = None
        secrets_dir: Optional[str] = None

    @classmethod
    def from_env(cls: Type[T], env: Optional[Environment] = None) -> T:
        """
        Create settings with values from the environment.

        Args:
            env: Optional environment type

        Returns:
            Settings instance with loaded values
        """
        instance = cls()

        # Get configuration class (use class Config or fallback to BaseSettings.Config)
        config = getattr(cls, "Config", BaseSettings.Config)

        # Load in order of increasing priority:

        # 1. Default values are already set in the class definition

        # 2. Load from standard env file (lowest priority)
        env_file = getattr(config, "env_file", None)
        if env_file and os.path.exists(env_file):
            # Handle JSON files directly - this is needed for proper boolean handling
            if env_file.endswith(".json"):
                try:
                    with open(env_file, "r") as f:
                        config_data = json.load(f)
                        for key, value in config_data.items():
                            if hasattr(instance, key):
                                setattr(instance, key, value)
                except (json.JSONDecodeError, IOError):
                    pass
            else:
                instance._load_from_file(env_file)

        # 2b. If an environment is specified, load from environment-specific file if it exists
        if env:
            env_specific_file = (
                f"{os.path.splitext(env_file)[0]}.{env.value}{os.path.splitext(env_file)[1]}"
                if env_file
                else f".env.{env.value}"
            )
            if os.path.exists(env_specific_file):
                instance._load_from_file(env_specific_file)

        # 3. Load from secrets directory (medium priority)
        secrets_dir = getattr(config, "secrets_dir", None)
        if secrets_dir and os.path.exists(secrets_dir):
            instance._load_from_secrets(secrets_dir)

        # 4. Load from environment variables (highest priority)
        instance._load_from_env_vars()

        return instance

    def _load_from_env_vars(self) -> None:
        """
        Load and apply settings from environment variables.

        Environment variables are converted to appropriate types based on the type
        annotations in the class definition. The method handles basic types (bool, int, float),
        as well as complex types like lists and dictionaries.

        For boolean values, the following strings are considered True:
        "true", "1", "yes", "y", "on" (case-insensitive).

        Empty values and invalid conversions are handled gracefully by keeping default values.
        """
        # Get type hints for proper type conversion
        type_hints = get_type_hints(self.__class__)

        # Get configured prefix
        config = getattr(self.__class__, "Config", BaseSettings.Config)
        prefix = getattr(config, "env_prefix", "")

        # Process each field
        for field_name, field_type in type_hints.items():
            # Skip private fields and methods
            if field_name.startswith("_"):
                continue

            # Check if env var exists
            env_name = f"{prefix}{field_name}"
            env_val = os.environ.get(env_name)

            # Skip if env var is not set or is empty
            if env_val is None or env_val.strip() == "":
                continue

            try:
                # Type conversion based on annotation
                if field_type == bool:
                    converted_value: Any = env_val.lower() in (
                        "true",
                        "1",
                        "yes",
                        "y",
                        "on",
                    )
                elif field_type == int:
                    converted_value = int(env_val)
                elif field_type == float:
                    converted_value = float(env_val)
                elif get_origin(field_type) is list or field_type == List:
                    # Handle list types - parse comma-separated values
                    converted_value = [item.strip() for item in env_val.split(",")]
                elif (
                    get_origin(field_type) is dict
                    or field_type == Dict
                    or field_type == dict
                ):
                    # Handle dictionary types - parse JSON
                    try:
                        converted_value = json.loads(env_val)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, keep the default
                        continue
                else:
                    converted_value = env_val

                # Set the value
                setattr(self, field_name, converted_value)
            except (ValueError, TypeError):
                # In case of conversion errors, keep the default value
                continue

    def _load_from_file(self, file_path: str) -> None:
        """
        Load and apply settings from a configuration file.

        Args:
            file_path: Path to the JSON or .env configuration file to load

        Supports both JSON format and .env file format.
        """
        # Ensure file exists before attempting to load
        if not os.path.exists(file_path):
            return

        if file_path.endswith(".json"):
            self._load_from_json_file(file_path)
        elif file_path.endswith(".env") or ".env." in file_path:
            self._load_from_dotenv_file(file_path)
        else:
            # Try to autodetect format
            try:
                with open(file_path, "r") as f:
                    content = f.read().strip()
                    if content.startswith("{"):
                        self._load_from_json_file(file_path)
                    else:
                        self._load_from_dotenv_file(file_path)
            except (IOError, UnicodeDecodeError):
                # Silently fail if file doesn't exist or is invalid
                pass

    def _load_from_json_file(self, file_path: str) -> None:
        """
        Load and apply settings from a JSON configuration file.

        Args:
            file_path: Path to the JSON configuration file to load
        """
        try:
            with open(file_path, "r") as f:
                config_data = json.load(f)

            # Get type hints for proper type conversion
            type_hints = get_type_hints(self.__class__)

            # Apply values from config file
            for key, value in config_data.items():
                if hasattr(self, key) and key in type_hints:
                    field_type = type_hints[key]

                    # Handle specific type conversions
                    if isinstance(value, str):
                        if field_type == bool:
                            value = value.lower() in ("true", "1", "yes", "y", "on")
                        elif field_type == int:
                            value = int(value)
                        elif field_type == float:
                            value = float(value)
                        elif get_origin(field_type) is list or field_type == List:
                            # Handle list types - parse comma-separated values
                            value = [item.strip() for item in value.split(",")]
                        elif get_origin(field_type) is dict or field_type == Dict:
                            # Handle dictionary types - parse JSON if string
                            try:
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                # Keep as is if not valid JSON
                                pass

                    setattr(self, key, value)
        except (json.JSONDecodeError, IOError):
            # Silently fail if file doesn't exist or is invalid
            pass

    def _load_from_dotenv_file(self, file_path: str) -> None:
        """
        Load and apply settings from a .env configuration file.

        Args:
            file_path: Path to the .env configuration file to load
        """
        type_hints = get_type_hints(self.__class__)

        try:
            with open(file_path, "r") as f:
                for line in f:
                    # Skip comments and empty lines
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Parse key-value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]

                        # Set in environment for subsequent env var lookup
                        os.environ[key] = value

                        # Also directly set on the instance if the key matches a field
                        field_name = key
                        config = getattr(self.__class__, "Config", BaseSettings.Config)
                        prefix = getattr(config, "env_prefix", "")
                        if prefix and key.startswith(prefix):
                            field_name = key[len(prefix) :]

                        if hasattr(self, field_name) and field_name in type_hints:
                            field_type = type_hints[field_name]

                            # Type conversion
                            if field_type == bool:
                                converted_value = value.lower() in (
                                    "true",
                                    "1",
                                    "yes",
                                    "y",
                                    "on",
                                )
                            elif field_type == int:
                                converted_value = int(value)
                            elif field_type == float:
                                converted_value = float(value)
                            elif get_origin(field_type) is list or field_type == List:
                                converted_value = [
                                    item.strip() for item in value.split(",")
                                ]
                            elif get_origin(field_type) is dict or field_type == Dict:
                                try:
                                    converted_value = json.loads(value)
                                except json.JSONDecodeError:
                                    converted_value = value
                            else:
                                converted_value = value

                            setattr(self, field_name, converted_value)
        except IOError:
            # Silently fail if file doesn't exist
            pass

    def _load_from_secrets(self, secrets_dir: str) -> None:
        """
        Load and apply settings from a secrets directory.

        Args:
            secrets_dir: Path to the directory containing secret files

        Each file in the directory should be named after a field in the settings class.
        The content of the file becomes the value for that field.
        """
        # Get type hints for proper type conversion
        type_hints = get_type_hints(self.__class__)

        for field_name in type_hints.keys():
            if field_name.startswith("_"):
                continue

            secret_path = Path(secrets_dir) / field_name
            if secret_path.exists():
                try:
                    with open(secret_path, "r") as f:
                        secret_value = f.read().strip()

                        # Type conversion based on annotation
                        field_type = type_hints[field_name]
                        if field_type == bool:
                            converted_value = secret_value.lower() in (
                                "true",
                                "1",
                                "yes",
                                "y",
                                "on",
                            )
                        elif field_type == int:
                            converted_value = int(secret_value)
                        elif field_type == float:
                            converted_value = float(secret_value)
                        elif get_origin(field_type) is list or field_type == List:
                            # Handle list types - parse comma-separated values
                            converted_value = [
                                item.strip() for item in secret_value.split(",")
                            ]
                        elif get_origin(field_type) is dict or field_type == Dict:
                            # Handle dictionary types - parse JSON
                            converted_value = json.loads(secret_value)
                        else:
                            converted_value = secret_value

                        setattr(self, field_name, converted_value)
                except IOError:
                    pass
