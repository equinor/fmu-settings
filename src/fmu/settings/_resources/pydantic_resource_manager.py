"""Contains the base class used for interacting with resources."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

from pydantic import BaseModel, ValidationError

from fmu.settings.types import ResettableBaseModel

from .cache_manager import CacheManager

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from pathlib import Path

    from fmu.settings._fmu_dir import FMUDirectoryBase

PydanticResource = TypeVar("PydanticResource", bound=BaseModel)
MutablePydanticResource = TypeVar("MutablePydanticResource", bound=ResettableBaseModel)


class PydanticResourceManager(Generic[PydanticResource]):
    """Base class for managing resources represented by Pydantic models."""

    def __init__(
        self: Self, fmu_dir: FMUDirectoryBase, model_class: type[PydanticResource]
    ) -> None:
        """Initializes the resource manager.

        Args:
            fmu_dir: The FMUDirectory instance
            model_class: The Pydantic model class this manager handles
        """
        self.fmu_dir = fmu_dir
        self.model_class = model_class
        self._cache: PydanticResource | None = None

    @property
    def relative_path(self: Self) -> Path:
        """Returns the path to the resource file _inside_ the .fmu directory.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

    @property
    def path(self: Self) -> Path:
        """Returns the full path to the resource file."""
        return self.fmu_dir.get_file_path(self.relative_path)

    @property
    def exists(self: Self) -> bool:
        """Returns whether or not the resource exists."""
        return self.path.exists()

    def load(
        self: Self, force: bool = False, store_cache: bool = True
    ) -> PydanticResource:
        """Loads the resource from disk and validates it as a Pydantic model.

        Args:
            force: Force a re-read even if the file is already cached.
            store_cache: Whether or not to cache the loaded model internally. This is
                best used with 'force=True' because if a model is already stored in
                _cache it will be returned without re-loading. Default True.

        Returns:
            Validated Pydantic model

        Raises:
            ValueError: If the resource file is missing or data does not match the
            model schema
        """
        if self._cache is None or force:
            if not self.exists:
                raise FileNotFoundError(
                    f"Resource file for '{self.__class__.__name__}' not found "
                    f"at: '{self.path}'"
                )

            try:
                content = self.fmu_dir.read_text_file(self.relative_path)
                data = json.loads(content)
                validated_model = self.model_class.model_validate(data)
                if store_cache:
                    self._cache = validated_model
                else:
                    return validated_model
            except ValidationError as e:
                raise ValueError(
                    f"Invalid content in resource file for '{self.__class__.__name__}: "
                    f"'{e}"
                ) from e
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON in resource file for '{self.__class__.__name__}': "
                    f"'{e}'"
                ) from e

        return self._cache

    def save(
        self: Self,
        model: PydanticResource,
        *,
        enable_revision_cache: bool | None = None,
        max_revisions: int | None = None,
    ) -> None:
        """Save the Pydantic model to disk.

        Args:
            model: Validated Pydantic model instance.
            enable_revision_cache: Override for whether to store a revision snapshot for
                this save. If None, fall back to the FMU directory setting.
            max_revisions: Override for how many snapshots to retain. If None, fall back
                to the FMU directory setting.
        """
        self.fmu_dir._lock.ensure_can_write()
        json_data = model.model_dump_json(by_alias=True, indent=2)
        self.fmu_dir.write_text_file(self.relative_path, json_data)

        if enable_revision_cache is None:
            enable_revision_cache = self.fmu_dir.enable_revision_cache

        if enable_revision_cache and self.exists:
            if max_revisions is None:
                cache = self.fmu_dir.cache
            else:
                cache = CacheManager(
                    self.fmu_dir,
                    cache_root=self.fmu_dir.revision_cache_root,
                    max_revisions=max_revisions,
                )
            cache.store_revision(self.relative_path, json_data)

        self._cache = model


class MutablePydanticResourceManager(PydanticResourceManager[MutablePydanticResource]):
    """Manages the .fmu configuration file."""

    def __init__(
        self: Self, fmu_dir: FMUDirectoryBase, config: type[MutablePydanticResource]
    ) -> None:
        """Initializes the Config resource manager."""
        super().__init__(fmu_dir, config)

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

            updated_config: MutablePydanticResource = config.model_validate(config_dict)
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

    def update(self: Self, updates: dict[str, Any]) -> MutablePydanticResource:
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

            updated_config: MutablePydanticResource = config.model_validate(config_dict)
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

    def reset(self: Self) -> MutablePydanticResource:
        """Resets the configuration to defaults.

        Returns:
            The new default config object
        """
        config = self.model_class.reset()
        self.save(config)
        return config
