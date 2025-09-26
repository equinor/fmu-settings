"""The generic configuration file in a .fmu directory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Self, TypeVar

from pydantic import ValidationError

from fmu.settings._logging import null_logger
from fmu.settings.models.project_config import ProjectConfig
from fmu.settings.models.user_config import UserConfig
from fmu.settings.types import ResettableBaseModel  # noqa: TC001

from .pydantic_resource_manager import PydanticResourceManager

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
        ProjectFMUDirectory,
        UserFMUDirectory,
    )

logger: Final = null_logger(__name__)

T = TypeVar("T", bound=ResettableBaseModel)


class ConfigManager(PydanticResourceManager[T]):
    """Manages the .fmu configuration file."""

    def __init__(self: Self, fmu_dir: FMUDirectoryBase, config: type[T]) -> None:
        """Initializes the Config resource manager."""
        super().__init__(fmu_dir, config)

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the config file."""
        return Path("config.json")

    def _get_dot_notation_key(
        self: Self, config_dict: dict[str, Any], key: str, default: Any = None
    ) -> Any:
        """Sets the value to a dot-notation key.

        Args:
            config_dict: The configuration dictionary we are modifying (by reference)
            key: The key to set
            default: Value to return if key is not found. Default None

        Returns:
            The value or default
        """
        parts = key.split(".")
        value = config_dict
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def get(self: Self, key: str, default: Any = None) -> Any:
        """Gets a configuration value by key.

        Supports dot notation for nested values (e.g., "foo.bar")

        Args:
            key: The configuration key
            default: Value to return if key is not found. Default None

        Returns:
            The configuration value or default
        """
        try:
            config = self.load()

            if "." in key:
                return self._get_dot_notation_key(config.model_dump(), key, default)

            if hasattr(config, key):
                return getattr(config, key)

            config_dict = config.model_dump()
            return config_dict.get(key, default)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Resource file for '{self.__class__.__name__}' not found "
                f"at: '{self.path}' when getting key {key}"
            ) from e

    def _set_dot_notation_key(
        self: Self, config_dict: dict[str, Any], key: str, value: Any
    ) -> None:
        """Sets the value to a dot-notation key.

        Args:
            config_dict: The configuration dictionary we are modifying (by reference)
            key: The key to set
            value: The value to set
        """
        parts = key.split(".")
        target = config_dict

        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]

        target[parts[-1]] = value

    def set(self: Self, key: str, value: Any) -> None:
        """Sets a configuration value by key.

        Args:
            key: The configuration key
            value: The value to set

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updated config is invalid
        """
        try:
            config = self.load()
            config_dict = config.model_dump()

            if "." in key:
                self._set_dot_notation_key(config_dict, key, value)
            else:
                config_dict[key] = value

            updated_config = config.model_validate(config_dict)
            self.save(updated_config)
        except ValidationError as e:
            raise ValueError(
                f"Invalid value set for '{self.__class__.__name__}' with "
                f"key '{key}', value '{value}': '{e}"
            ) from e
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Resource file for '{self.__class__.__name__}' not found "
                f"at: '{self.path}' when setting key {key}"
            ) from e

    def update(self: Self, updates: dict[str, Any]) -> T:
        """Updates multiple configuration values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated Config object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updates config is invalid
        """
        try:
            config = self.load()
            config_dict = config.model_dump()

            flat_updates = {k: v for k, v in updates.items() if "." not in k}
            config_dict.update(flat_updates)

            for key, value in updates.items():
                if "." in key:
                    self._set_dot_notation_key(config_dict, key, value)

                updated_config = config.model_validate(config_dict)
            self.save(updated_config)
        except ValidationError as e:
            raise ValueError(
                f"Invalid value set for '{self.__class__.__name__}' with "
                f"updates '{updates}': '{e}"
            ) from e
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Resource file for '{self.__class__.__name__}' not found "
                f"at: '{self.path}' when setting updates {updates}"
            ) from e

        return updated_config

    def reset(self: Self) -> T:
        """Resets the configuration to defaults.

        Returns:
            The new default config object
        """
        config = self.model_class.reset()
        self.save(config)
        return config


class ProjectConfigManager(ConfigManager[ProjectConfig]):
    """Manages the .fmu configuration file in a project."""

    def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initializes the ProjectConfig resource manager."""
        super().__init__(fmu_dir, ProjectConfig)


class UserConfigManager(ConfigManager[UserConfig]):
    """Manages the .fmu configuration file in a user's home directory."""

    def __init__(self: Self, fmu_dir: UserFMUDirectory) -> None:
        """Initializes the UserConfig resource manager."""
        super().__init__(fmu_dir, UserConfig)
