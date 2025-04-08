"""
Base configuration system for applications.

A simple, consistent configuration management system that loads settings
from environment variables, files, and secrets directories.
"""

import json
import os
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

        # 1. Load from file first (lowest priority)
        env_file = getattr(config, "env_file", None)
        if env_file and os.path.exists(env_file):
            instance._load_from_file(env_file)

        # 2. Load from secrets directory
        secrets_dir = getattr(config, "secrets_dir", None)
        if secrets_dir and os.path.exists(secrets_dir):
            instance._load_from_secrets(secrets_dir)

        # 3. Load from environment variables (highest priority)
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

            if env_val is not None:
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
                elif get_origin(field_type) is dict or field_type == Dict:
                    # Handle dictionary types - parse JSON
                    converted_value = json.loads(env_val)
                else:
                    converted_value = env_val

                # Set the value
                setattr(self, field_name, converted_value)

    def _load_from_file(self, file_path: str) -> None:
        """
        Load and apply settings from a configuration file.

        Args:
            file_path: Path to the JSON configuration file to load

        Currently only supports JSON format. The method reads the file and sets
        attributes on the instance that match keys in the JSON object.
        """
        if not file_path.endswith(".json"):
            return

        try:
            with open(file_path, "r") as f:
                config_data = json.load(f)

            # Apply values from config file
            for key, value in config_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        except (json.JSONDecodeError, IOError):
            # Silently fail if file doesn't exist or is invalid
            pass

    def _load_from_secrets(self, secrets_dir: str) -> None:
        """
        Load and apply settings from a secrets directory.

        Args:
            secrets_dir: Path to the directory containing secret files

        Each file in the directory should be named after a field in the settings class.
        The content of the file becomes the value for that field.
        """
        for field_name in get_type_hints(self.__class__).keys():
            if field_name.startswith("_"):
                continue

            secret_path = Path(secrets_dir) / field_name
            if secret_path.exists():
                try:
                    with open(secret_path, "r") as f:
                        secret_value = f.read().strip()
                        setattr(self, field_name, secret_value)
                except IOError:
                    pass
