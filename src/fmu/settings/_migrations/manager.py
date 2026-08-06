"""Forward-only migration support for versioned data."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any, Final, Generic, Literal, TypeVar, get_args, get_origin

from pydantic import BaseModel, ValidationError

MigratableResource = TypeVar("MigratableResource", bound=BaseModel)
MigrationFunction = Callable[[dict[str, Any]], dict[str, Any]]

LEGACY_SCHEMA_VERSION: Final = 1
"""Version assigned to resources written before ``schema_version`` existed."""


class MigrationError(ValueError):
    """Raised when a resource cannot be migrated to the current schema."""


class MigrationManager(Generic[MigratableResource]):
    """Migrate stored data to its current schema."""

    def __init__(
        self,
        model_class: type[MigratableResource],
        migrations: Mapping[int, MigrationFunction],
    ) -> None:
        """Initialize a migration manager.

        Args:
            model_class: Current Pydantic model for the resource.
            migrations: Migration functions keyed by their source schema version.

        Raises:
            TypeError: If the model does not declare one positive integer
                ``schema_version`` literal with the same default value.
        """
        self.model_class = model_class
        self.migrations = dict(migrations)
        self.current_version = self._get_current_version()

    def migrate_resource(self, data: Any) -> MigratableResource:
        """Migrate decoded data with registered migration functions and validate it.

        Each migration function must increment the schema version by exactly one.

        Args:
            data: Decoded JSON data to migrate and validate.

        Returns:
            The migrated data as a validated current model.

        Raises:
            MigrationError: If the data is not a JSON object, a schema version is
                invalid or newer than supported, a required migration function is
                missing or fails, a migration function does not increment the schema
                version by one, or the final data does not match the current model.
        """
        if not isinstance(data, dict):
            raise MigrationError(
                f"{self.model_class.__name__} resource must be a JSON object"
            )
        source_schema_version = self._get_source_schema_version(data)
        migration_steps = self._get_migration_steps(source_schema_version)
        migrated_data = copy.deepcopy(data) if migration_steps else data.copy()
        migrated_data.setdefault("schema_version", source_schema_version)
        for version, migration_function in migration_steps:
            try:
                migrated_data = migration_function(migrated_data)
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

    def requires_migration(self, data: dict[str, Any]) -> bool:
        """Return whether stored data needs migration before a write.

        This check verifies that all required forward migration functions exist and
        that the stored schema version is older than the current schema version.

        Args:
            data: Existing stored data that a write would replace.

        Returns:
            Whether the stored data requires migration.

        Raises:
            MigrationError: If the schema version is invalid or newer than supported,
                or a required migration function is missing.
        """
        source_schema_version = self._get_source_schema_version(data)
        self._get_migration_steps(source_schema_version)
        return source_schema_version < self.current_version

    def _get_migration_steps(
        self, source_schema_version: int
    ) -> list[tuple[int, MigrationFunction]]:
        """Return and validate migration steps needed by a source schema version."""
        if source_schema_version > self.current_version:
            raise MigrationError(
                f"{self.model_class.__name__} schema version {source_schema_version} "
                "is newer than supported version "
                f"{self.current_version}; downgrade migration "
                "is not supported"
            )

        steps: list[tuple[int, MigrationFunction]] = []
        for version in range(source_schema_version, self.current_version):
            migration_function = self.migrations.get(version)
            if migration_function is None:
                raise MigrationError(
                    f"Missing {self.model_class.__name__} migration function from "
                    "schema "
                    f"version {version} to {version + 1}"
                )
            steps.append((version, migration_function))
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

    def _get_source_schema_version(self, data: dict[str, Any]) -> int:
        """Return the stored schema version, using the legacy version when absent."""
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
