"""
Base configuration system for applications.

A simple, consistent configuration management system that loads settings
from environment variables, files, and secrets directories.
"""

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union, cast, get_type_hints

T = TypeVar("T", bound="BaseSettings")


class Environment(str, Enum):
    """Environment types for configuration loading."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class BaseSettings:
    """
    Base class for application settings.

    Provides methods to load settings from multiple sources in priority order:
    1. Environment variables
    2. Secrets directory
    3. Environment file
    4. Default values
    """

    class Config:
        """Configuration for settings behavior."""

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
        """Load and apply settings from environment variables."""
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
                    converted_value: Any = env_val.lower() in ("true", "1", "yes")
                elif field_type == int:
                    converted_value = int(env_val)
                elif field_type == float:
                    converted_value = float(env_val)
                else:
                    converted_value = env_val

                # Set the value
                setattr(self, field_name, converted_value)

    def _load_from_file(self, file_path: str) -> None:
        """Load and apply settings from a configuration file."""
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
        """Load and apply settings from a secrets directory."""
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
