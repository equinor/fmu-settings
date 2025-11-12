"""Contains the base class used for interacting with resources."""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

from pydantic import BaseModel, ValidationError

from fmu.settings.models.project_config import ProjectConfig
from fmu.settings.types import ResettableBaseModel

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from pathlib import Path

    from fmu.settings._fmu_dir import FMUDirectoryBase

PydanticResource = TypeVar("PydanticResource", bound=BaseModel)
MutablePydanticResource = TypeVar("MutablePydanticResource", bound=ResettableBaseModel)


class PydanticResourceManager(Generic[PydanticResource]):
    """Base class for managing resources represented by Pydantic models."""

    automatic_caching: bool = True

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

    @staticmethod
    def _get_dot_notation_key(
        resource_dict: dict[str, Any], key: str, default: Any = None
    ) -> Any:
        """Get a value from the resource by a dot-notation key.

        Args:
            resource_dict: The resource dictionary to get the value from
            key: The key to the value in the resource
            default: Value to return if key is not found. Default None

        Returns:
            The value or default
        """
        parts = key.split(".")
        value = resource_dict
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

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
    ) -> None:
        """Save the Pydantic model to disk.

        Args:
            model: Validated Pydantic model instance.
        """
        self.fmu_dir._lock.ensure_can_write()
        json_data = model.model_dump_json(by_alias=True, indent=2)
        self.fmu_dir.write_text_file(self.relative_path, json_data)

        if self.automatic_caching and self.exists:
            self.fmu_dir.cache.store_revision(self.relative_path, json_data)

        self._cache = model


class MutablePydanticResourceManager(PydanticResourceManager[MutablePydanticResource]):
    """Manages the .fmu resource file."""

    def __init__(
        self: Self, fmu_dir: FMUDirectoryBase, resource: type[MutablePydanticResource]
    ) -> None:
        """Initializes the resource manager."""
        super().__init__(fmu_dir, resource)

    def get(self: Self, key: str, default: Any = None) -> Any:
        """Gets a resource value by key.

        Supports dot notation for nested values (e.g., "foo.bar")

        Args:
            key: The resource key
            default: Value to return if key is not found. Default None

        Returns:
            The resource value or default
        """
        try:
            resource = self.load()

            if "." in key:
                return self._get_dot_notation_key(resource.model_dump(), key, default)

            if hasattr(resource, key):
                return getattr(resource, key)

            resource_dict = resource.model_dump()
            return resource_dict.get(key, default)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Resource file for '{self.__class__.__name__}' not found "
                f"at: '{self.path}' when getting key {key}"
            ) from e

    def _set_dot_notation_key(
        self: Self, resource_dict: dict[str, Any], key: str, value: Any
    ) -> None:
        """Sets the value to a dot-notation key.

        Args:
            resource_dict: The resource dictionary we are modifying (by reference)
            key: The key to set
            value: The value to set
        """
        parts = key.split(".")
        target = resource_dict

        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]

        target[parts[-1]] = value

    def set(self: Self, key: str, value: Any) -> None:
        """Sets a resource value by key.

        Args:
            key: The resource key
            value: The value to set

        Raises:
            FileNotFoundError: If resource file doesn't exist
            ValueError: If the updated resource is invalid
        """
        try:
            resource = self.load()
            resource_dict = resource.model_dump()
            old_resource_dict = copy.deepcopy(resource_dict)

            if "." in key:
                self._set_dot_notation_key(resource_dict, key, value)
            else:
                resource_dict[key] = value

            updated_resource = resource.model_validate(resource_dict)
            self.save(updated_resource)

            if self.model_class == ProjectConfig:
                self.fmu_dir._changelog.log_update_to_changelog(
                    updates={key: value},
                    old_resource_dict=old_resource_dict,
                    relative_path=self.relative_path,
                )

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
        """Updates multiple resource values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated Resource object

        Raises:
            FileNotFoundError: If resource file doesn't exist
            ValueError: If the updates resource is invalid
        """
        try:
            resource = self.load()
            resource_dict = resource.model_dump()
            old_resource_dict = copy.deepcopy(resource_dict)

            flat_updates = {k: v for k, v in updates.items() if "." not in k}
            resource_dict.update(flat_updates)

            for key, value in updates.items():
                if "." in key:
                    self._set_dot_notation_key(resource_dict, key, value)

            updated_resource = resource.model_validate(resource_dict)
            self.save(updated_resource)

            if self.model_class == ProjectConfig:
                self.fmu_dir._changelog.log_update_to_changelog(
                    updates, old_resource_dict, self.relative_path
                )

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

        return updated_resource

    def reset(self: Self) -> MutablePydanticResource:
        """Resets the resources to defaults.

        Returns:
            The new default resource object
        """
        resource = self.model_class.reset()
        self.save(resource)
        return resource
