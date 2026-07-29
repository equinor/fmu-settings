"""Forward-only migration support for versioned resource data."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any, Final, Generic, Literal, TypeVar, get_args, get_origin

from pydantic import BaseModel, ValidationError

MigratableResource = TypeVar("MigratableResource", bound=BaseModel)
Migration = Callable[[dict[str, Any]], dict[str, Any]]

LEGACY_SCHEMA_VERSION: Final = 1
"""Version assigned to resources written before ``schema_version`` existed."""


class MigrationError(ValueError):
    """Raised when a resource cannot be migrated to the current schema."""


class MigrationManager(Generic[MigratableResource]):
    """Migrate versioned resource data to its current schema."""

    def __init__(
        self,
        model_class: type[MigratableResource],
        migrations: Mapping[int, Migration],
    ) -> None:
        """Initialize a migration manager.

        Args:
            model_class: Current Pydantic model for the resource.
            migrations: Migration functions keyed by their source version.

        Raises:
            TypeError: If the model does not declare one positive integer
                ``schema_version`` literal with the same default value.
        """
        self.model_class = model_class
        self.migrations = dict(migrations)
        self.current_version = self._get_current_version()

    def migrate_resource(self, data: Any) -> MigratableResource:
        """Migrate decoded JSON data and return a validated current model.

        Each migration must advance the schema by exactly one version.

        Args:
            data: Decoded JSON data to migrate and validate.

        Returns:
            The resource data as a validated current model.

        Raises:
            MigrationError: If the data is not a JSON object, a schema version is
                invalid or newer than supported, a required migration is missing or
                fails, a migration does not advance by one version, or the final data
                does not match the current model.
        """
        if not isinstance(data, dict):
            raise MigrationError(
                f"{self.model_class.__name__} resource must be a JSON object"
            )
        source_version = self._get_source_version(data)
        migration_steps = self._get_migration_steps(source_version)
        migrated_data = copy.deepcopy(data) if migration_steps else data.copy()
        migrated_data.setdefault("schema_version", source_version)
        for version, migration in migration_steps:
            try:
                migrated_data = migration(migrated_data)
            except Exception as e:
                raise MigrationError(
                    f"{self.model_class.__name__} migration from schema version "
                    f"{version} to {version + 1} failed"
                ) from e

            result_version = self._validate_version(migrated_data.get("schema_version"))
            expected_version = version + 1
            if result_version != expected_version:
                raise MigrationError(
                    f"{self.model_class.__name__} migration from schema version "
                    f"{version} must set schema_version to {expected_version}, "
                    f"but set it to {result_version}"
                )

        try:
            validated_model = self.model_class.model_validate(migrated_data)
        except ValidationError as e:
            raise MigrationError(
                f"{self.model_class.__name__} data does not validate against current "
                f"schema version {self.current_version}"
            ) from e

        return validated_model

    def requires_backup(self, data: dict[str, Any]) -> bool:
        """Return whether to back up the original data before a write.

        This method does not run migrations. It confirms that all required forward
        migration steps exist, then requires a backup for unversioned or older data.

        Args:
            data: Existing resource data that a write would replace.

        Returns:
            Whether the original resource data must be backed up.

        Raises:
            MigrationError: If the schema version is invalid or newer than supported,
                or a required migration step is missing.
        """
        source_version = self._get_source_version(data)
        self._get_migration_steps(source_version)
        is_unversioned = "schema_version" not in data
        is_outdated = source_version < self.current_version
        return is_unversioned or is_outdated

    def _get_migration_steps(self, source_version: int) -> list[tuple[int, Migration]]:
        """Return and validate all migration steps needed by a source version."""
        if source_version > self.current_version:
            raise MigrationError(
                f"{self.model_class.__name__} schema version {source_version} is newer "
                f"than supported version {self.current_version}; downgrade migration "
                "is not supported"
            )

        steps: list[tuple[int, Migration]] = []
        for version in range(source_version, self.current_version):
            migration = self.migrations.get(version)
            if migration is None:
                raise MigrationError(
                    f"Missing {self.model_class.__name__} migration from schema "
                    f"version {version} to {version + 1}"
                )
            steps.append((version, migration))
        return steps

    def _get_current_version(self) -> int:
        """Return the schema version declared by the current model.

        The model must define ``schema_version`` as one positive integer
        ``Literal`` and use the same integer as its default value. For example,
        schema version 2 must be declared as ``schema_version: Literal[2] = 2``.

        Returns:
            The current schema version.

        Raises:
            TypeError: If the model does not declare a valid schema version.
        """
        schema_field = self.model_class.model_fields.get("schema_version")
        if schema_field is None:
            raise TypeError(
                f"{self.model_class.__name__} must define a schema_version field"
            )

        if get_origin(schema_field.annotation) is not Literal:
            raise TypeError(
                f"{self.model_class.__name__}.schema_version must use Literal[int]"
            )

        literal_versions = get_args(schema_field.annotation)
        if len(literal_versions) != 1:
            raise TypeError(
                f"{self.model_class.__name__}.schema_version must contain one version"
            )

        try:
            current_version = self._validate_version(literal_versions[0])
        except MigrationError as e:
            raise TypeError(str(e)) from e

        if schema_field.default != current_version:
            raise TypeError(
                f"{self.model_class.__name__}.schema_version must default to "
                f"{current_version}"
            )
        return current_version

    def _get_source_version(self, data: dict[str, Any]) -> int:
        """Get the source version, using the legacy version when it is absent."""
        if "schema_version" not in data:
            return LEGACY_SCHEMA_VERSION
        return self._validate_version(data.get("schema_version"))

    @staticmethod
    def _validate_version(value: Any) -> int:
        """Validate a schema version value."""
        # bool is a subclass of int, so it must be rejected explicitly.
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise MigrationError("Schema version must be a positive integer")
        return value
