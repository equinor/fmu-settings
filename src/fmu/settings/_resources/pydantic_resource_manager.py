"""Contains the base class used for interacting with resources."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Generic, Self, TypeVar

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from pathlib import Path

    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import FMUDirectoryBase

T = TypeVar("T", bound=BaseModel)


class PydanticResourceManager(Generic[T]):
    """Base class for managing resources represented by Pydantic models."""

    def __init__(self: Self, fmu_dir: FMUDirectoryBase, model_class: type[T]) -> None:
        """Initializes the resource manager.

        Args:
            fmu_dir: The FMUDirectory instance
            model_class: The Pydantic model class this manager handles
        """
        self.fmu_dir = fmu_dir
        self.model_class = model_class
        self._cache: T | None = None

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

    def load(self: Self, force: bool = False) -> T:
        """Loads the resources from disk and validates it as a Pydantic model.

        Args:
            force: Force a re-read even if the file is already cached

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
                self._cache = self.model_class.model_validate(data)
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

    def save(self: Self, model: T) -> None:
        """Save the Pydantic model to disk.

        Args:
            model: Validated Pydantic model instance
        """
        json_data = model.model_dump_json(by_alias=True, indent=2)
        self.fmu_dir.write_text_file(self.relative_path, json_data)
        self._cache = model
