"""Contains the base class used for interacting with resources."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Generic, Self, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from fmu.settings._logging import null_logger
from fmu.settings._migrations import (
    MigrationError,
    MigrationManager,
)
from fmu.settings._utils import path_exists
from fmu.settings.models.diff import (
    ListFieldDiff,
    ListUpdatedEntry,
    ResourceDiff,
    ScalarFieldDiff,
)
from fmu.settings.types import ResettableBaseModel

if TYPE_CHECKING:
    from collections.abc import Mapping

    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import FMUDirectoryBase

PydanticResource = TypeVar("PydanticResource", bound=BaseModel)
MutablePydanticResource = TypeVar("MutablePydanticResource", bound=ResettableBaseModel)

MIGRATION_BACKUP_DIRECTORY: Final = Path("migration-backups")
MIGRATION_BACKUP_FILENAME_TEMPLATE: Final = (
    "{timestamp}-{token}-{model_name}-v{schema_version}{suffix}"
)
logger: Final = null_logger(__name__)


class PydanticResourceManager(Generic[PydanticResource]):
    """Base class for managing resources represented by Pydantic models."""

    automatic_caching: bool = True

    def __init__(
        self: Self,
        fmu_dir: FMUDirectoryBase,
        model_class: type[PydanticResource],
        *,
        migration_manager: MigrationManager[PydanticResource] | None = None,
    ) -> None:
        """Initializes the resource manager.

        Args:
            fmu_dir: The FMUDirectory instance
            model_class: The Pydantic model class this manager handles
            migration_manager: Optional migration manager for versioned resources
        """
        self.fmu_dir = fmu_dir
        self.model_class = model_class
        if (
            migration_manager is not None
            and migration_manager.model_class is not model_class
        ):
            raise TypeError(
                "Migration manager model must match the resource manager model"
            )
        self.migration_manager = migration_manager
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
        return path_exists(self.path)

    @property
    def diff_list_keys(self: Self) -> Mapping[str, str | tuple[str, ...]]:
        """Return list field paths and their identity keys used for list diffs."""
        return {}

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
            FileNotFoundError: If the resource file does not exist.
            MigrationError: If the resource cannot be migrated to the current schema.
            ValueError: If the resource file contains invalid JSON or does not match
                the model schema.
        """
        if self._cache is None or force:
            if not self.exists:
                raise FileNotFoundError(
                    f"Resource file for '{self.__class__.__name__}' not found "
                    f"at: '{self.path}'"
                )

            try:
                content = self.fmu_dir.read_text_file(self.relative_path)
                validated_model = self._migrate_and_validate_stored_data(
                    json.loads(content)
                )
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

    def _migrate_and_validate_stored_data(self: Self, data: Any) -> PydanticResource:
        """Validate decoded stored data, migrating it forward when required."""
        if (
            self.migration_manager is not None
            and self.migration_manager.requires_migration(data)
        ):
            return self.migration_manager.migrate_resource(data)
        return self.model_class.model_validate(data)

    def save(
        self: Self,
        model: PydanticResource,
    ) -> None:
        """Save the Pydantic model and preserve stored data that needs migration.

        Before overwriting older stored data, save its original content as a manual
        migration backup and a normal cache revision.

        Args:
            model: Validated Pydantic model instance.

        Raises:
            MigrationError: If the stored schema version cannot be checked or cannot
                be migrated to the current version.
            PermissionError: If another process holds the write lock.
        """
        self.fmu_dir._lock.ensure_can_write()

        migration_manager = self.migration_manager
        if migration_manager is not None:
            try:
                content = self.fmu_dir.read_text_file(self.relative_path)
                data = json.loads(content)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            else:
                if isinstance(data, dict):
                    try:
                        requires_migration = migration_manager.requires_migration(data)
                    except MigrationError as e:
                        raise MigrationError(
                            "Failed to check migration requirements for resource "
                            f"file '{self.__class__.__name__}' at '{self.path}': {e}"
                        ) from e

                    if requires_migration:
                        source_schema_version = data.get("schema_version", 1)
                        self._write_migration_backup(
                            content,
                            source_schema_version,
                        )
                        if self.automatic_caching:
                            self.fmu_dir.cache.store_revision(
                                self.relative_path,
                                content,
                            )

        json_data = model.model_dump_json(by_alias=True, indent=2)
        self.fmu_dir.write_text_file(self.relative_path, json_data)

        if self.automatic_caching and self.exists:
            self.fmu_dir.cache.store_revision(self.relative_path, json_data)

        self._cache = model

    def restore_from_cache(self: Self, revision_id: str) -> None:
        """Restore the resource file from a cache revision.

        The current state is cached first when it is valid, so the restore can be
        undone.

        Args:
            revision_id: The revision filename to restore from.

        Raises:
            FileNotFoundError: If the cache revision doesn't exist.
            MigrationError: If the cached content cannot be migrated to the current
                schema.
            ValueError: If the cached content is invalid JSON or fails model
                validation.
        """
        self.fmu_dir.cache.restore_revision(
            self.relative_path,
            revision_id,
            model_class=self.model_class,
            migration_manager=self.migration_manager,
        )
        self.load(force=True)

    def _write_migration_backup(
        self: Self, content: str, source_schema_version: int
    ) -> None:
        """Write a best-effort migration backup of the original content.

        For example, a ``config.json`` backup can be stored under
        ``.fmu/migration-backups/config/`` as
        ``<timestamp>-<token>-ProjectConfig-v1.json``.
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        token = uuid4().hex[:8]
        backup_filename = MIGRATION_BACKUP_FILENAME_TEMPLATE.format(
            timestamp=timestamp,
            token=token,
            model_name=self.model_class.__name__,
            schema_version=source_schema_version,
            suffix=self.relative_path.suffix,
        )
        backup_path = self._migration_backup_directory / backup_filename

        try:
            self.fmu_dir.write_text_file(backup_path, content)
        except OSError as e:
            logger.warning(
                f"Failed to save migration backup for '{self.path}' at "
                f"'{self.fmu_dir.get_file_path(backup_path)}'. "
                f"Continuing without it: {e}"
            )

    @property
    def _migration_backup_directory(self: Self) -> Path:
        """Return the migration backup directory relative to ``.fmu``."""
        return (
            MIGRATION_BACKUP_DIRECTORY
            / self.relative_path.parent
            / self.relative_path.stem
        )

    @property
    def _migration_backup_filename_pattern(self: Self) -> re.Pattern[str]:
        """Return the migration backup filename pattern from the shared template."""
        return re.compile(
            MIGRATION_BACKUP_FILENAME_TEMPLATE.format(
                timestamp=r"\d{8}T\d{6}\.\d{6}Z",
                token=r"[0-9a-f]{8}",
                model_name=re.escape(self.model_class.__name__),
                schema_version=r"\d+",
                suffix=re.escape(self.relative_path.suffix),
            )
        )

    def find_latest_compatible_migration_backup(
        self: Self,
    ) -> tuple[Path, PydanticResource] | None:
        """Return the newest migration backup that validates with this schema.

        Only files that match ``_migration_backup_filename_pattern`` are checked,
        from newest to oldest. A backup is compatible if it validates
        directly or after forward migration. Unreadable, invalid, and
        newer-schema backups are skipped.

        Returns:
            The backup path relative to ``.fmu`` and its validated model, or None
            if no compatible backup exists.
        """
        filename_pattern = self._migration_backup_filename_pattern
        backup_files = sorted(
            (
                path
                for path in self.fmu_dir.list_files(self._migration_backup_directory)
                if filename_pattern.fullmatch(path.name)
            ),
            key=lambda path: path.name,
            reverse=True,
        )
        for backup_file in backup_files:
            backup_path = self._migration_backup_directory / backup_file.name
            try:
                content = self.fmu_dir.read_text_file(backup_path)
                model = self._migrate_and_validate_stored_data(json.loads(content))
            except (OSError, ValueError) as e:
                logger.debug(
                    f"Skipped incompatible migration backup {backup_path}: {e}"
                )
                continue
            return backup_path, model
        return None

    def restore_from_migration_backup(self: Self, backup: PydanticResource) -> None:
        """Overwrite the resource file with a validated migration backup.

        The current file is not read or cached, so this also works when it cannot
        be loaded with the installed schema.

        Args:
            backup: A backup model from ``find_latest_compatible_migration_backup``.

        Raises:
            PermissionError: If another process holds the write lock.
        """
        self.fmu_dir.write_text_file(
            self.relative_path, backup.model_dump_json(by_alias=True, indent=2)
        )
        self._cache = backup

    def get_model_diff(
        self: Self,
        current_model: BaseModel,
        incoming_model: BaseModel,
        prefix: str = "",
    ) -> list[tuple[str, Any, Any]]:
        """Recursively get differences between two Pydantic models.

        Returns:
            A list of differences between the models on field level.
        """
        if type(incoming_model) is not type(current_model):
            raise ValueError(
                "Models must be of the same type. Current model is of type "
                f"'{current_model.__class__.__name__}', incoming model of type "
                f"'{incoming_model.__class__.__name__}'."
            )

        changes: list[tuple[str, Any, Any]] = []
        diff_ignore_fields = getattr(self, "diff_ignore_fields", [])

        for field_name in type(current_model).model_fields:
            if field_name in diff_ignore_fields:
                continue

            current_value = getattr(current_model, field_name)
            incoming_value = getattr(incoming_model, field_name)

            field_path = f"{prefix}.{field_name}" if prefix else field_name

            if current_value is None and incoming_value is not None:
                changes.append((field_path, None, incoming_value))
                continue

            if current_value is not None and incoming_value is None:
                changes.append((field_path, current_value, None))
                continue

            if isinstance(current_value, BaseModel) and isinstance(
                incoming_value, BaseModel
            ):
                changes.extend(
                    self.get_model_diff(current_value, incoming_value, field_path)
                )
                continue

            if current_value != incoming_value:
                changes.append((field_path, current_value, incoming_value))

        return changes

    def get_structured_model_diff(
        self: Self,
        current_model: BaseModel,
        incoming_model: BaseModel,
    ) -> list[ResourceDiff]:
        """Return a diff that is easier to show in the UI.

        Scalar fields are returned as simple ``before``/``after`` values.

        For list fields in ``diff_list_keys``, this returns only the items that
        changed (``added``, ``removed``, ``updated``), using the configured identity
        key. Updated items include only their changed fields. A list that changes
        to or from ``None`` is returned as a scalar diff.
        """
        changes = self.get_model_diff(current_model, incoming_model)

        results: list[ResourceDiff] = []

        for field_path, before, after in changes:
            list_key = self.diff_list_keys.get(field_path)
            if list_key is None or before is None or after is None:
                results.append(
                    ScalarFieldDiff(
                        field_path=field_path,
                        before=self._dump_diff_value(before),
                        after=self._dump_diff_value(after),
                    )
                )
                continue

            before_map = self._build_list_item_map(before, list_key)
            after_map = self._build_list_item_map(after, list_key)

            before_keys = set(before_map)
            after_keys = set(after_map)

            added = [
                self._dump_diff_value(after_map[key])
                for key in sorted(after_keys - before_keys, key=str)
            ]
            removed = [
                self._dump_diff_value(before_map[key])
                for key in sorted(before_keys - after_keys, key=str)
            ]
            updated: list[ListUpdatedEntry] = []
            for key in sorted(before_keys & after_keys, key=str):
                item_changes = self.get_model_diff(before_map[key], after_map[key])
                if not item_changes:
                    continue
                updated.append(
                    ListUpdatedEntry(
                        key=key,
                        before={
                            path: self._dump_diff_value(old)
                            for path, old, _ in item_changes
                        },
                        after={
                            path: self._dump_diff_value(new)
                            for path, _, new in item_changes
                        },
                    )
                )

            results.append(
                ListFieldDiff(
                    field_path=field_path,
                    added=added,
                    removed=removed,
                    updated=updated,
                )
            )

        return results

    def _build_list_item_map(
        self: Self, items: list[Any], list_key: str | tuple[str, ...]
    ) -> dict[object, Any]:
        """Build a lookup map for list diffing using a configured identity key."""
        if isinstance(list_key, str):
            return {getattr(item, list_key): item for item in items}
        return {
            tuple(getattr(item, field) for field in list_key): item for item in items
        }

    def get_resource_diff(
        self: Self, incoming_resource: PydanticResourceManager[PydanticResource]
    ) -> list[tuple[str, Any, Any]]:
        """Get differences between current and incoming Pydantic resource.

        Returns:
            A list of differences between the resources.
        """
        if self.exists and incoming_resource.exists:
            current_model = self.load()
            incoming_model = incoming_resource.load()
            if type(current_model) is not type(incoming_model):
                raise TypeError(
                    f"Resources to diff must be of the same type. Current resource is "
                    f"of type '{self.model_class.__name__}', incoming resource of type "
                    f"'{incoming_model.__class__.__name__}'."
                )
            return self.get_model_diff(current_model, incoming_model)
        raise FileNotFoundError(
            "Resources to diff must exist in both directories: "
            f"Current resource {str(self.relative_path)} exists: {self.exists}. "
            f"Incoming resource {str(incoming_resource.relative_path)} exists: "
            f"{incoming_resource.exists}."
        )

    @staticmethod
    def _dump_diff_value(value: Any) -> Any:
        """Convert BaseModel values to JSON-serializable structures."""
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json", by_alias=True)
        return value


class MutablePydanticResourceManager(PydanticResourceManager[MutablePydanticResource]):
    """Manages the .fmu resource file."""

    def __init__(
        self: Self,
        fmu_dir: FMUDirectoryBase,
        resource: type[MutablePydanticResource],
        *,
        migration_manager: MigrationManager[MutablePydanticResource] | None = None,
    ) -> None:
        """Initializes the resource manager."""
        super().__init__(
            fmu_dir,
            resource,
            migration_manager=migration_manager,
        )

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

            if "." in key:
                self._set_dot_notation_key(resource_dict, key, value)
            else:
                resource_dict[key] = value

            updated_resource = resource.model_validate(resource_dict)
            self.save(updated_resource)

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

            flat_updates = {k: v for k, v in updates.items() if "." not in k}
            resource_dict.update(flat_updates)

            for key, value in updates.items():
                if "." in key:
                    self._set_dot_notation_key(resource_dict, key, value)

            updated_resource = resource.model_validate(resource_dict)
            self.save(updated_resource)

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

        return self.load()

    def reset(self: Self) -> MutablePydanticResource:
        """Resets the resources to defaults.

        Returns:
            The new default resource object
        """
        resource = self.model_class.reset()
        self.save(resource)
        return resource

    def merge_resource(
        self: Self,
        incoming_resource: MutablePydanticResourceManager[MutablePydanticResource],
    ) -> MutablePydanticResource:
        """Merge an incoming Pydantic resource into the current resource model.

        All changes in the incoming resource will be applied.

        Returns:
            The updated resource object
        """
        try:
            changes: list[tuple[str, Any, Any]] = self.get_resource_diff(
                incoming_resource
            )
            return self.merge_changes(changes)
        except TypeError as e:
            raise TypeError(
                f"Merging pydantic resource failed. The incoming resource must be of "
                f"type '{self.model_class.__name__}'. The provided model was of type "
                f"'{incoming_resource.model_class.__name__}'."
            ) from e

    def merge_changes(
        self: Self, changes: list[tuple[str, Any, Any]]
    ) -> MutablePydanticResource:
        """Merge a list of changes into the current resource model.

        All changes will overwrite the current values.

        Returns:
            The updated resource object
        """
        updates: dict[str, Any] = {}
        for change in changes:
            updates[change[0]] = change[2]
        return self.update(updates)
