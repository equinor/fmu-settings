"""Tests for forward-only resource migrations."""

from __future__ import annotations

from typing import Any, Literal, cast

import pytest
from pydantic import BaseModel

from fmu.settings import MigrationError
from fmu.settings._migrations import MigrationManager


class VersionThreeModel(BaseModel):
    """Test-only model for a resource at schema version three."""

    schema_version: Literal[3] = 3
    value: str
    migrations_applied: list[int]


class VersionOneModel(BaseModel):
    """Test-only model for a resource at schema version one."""

    schema_version: Literal[1] = 1
    value: str


def migrate_one_to_two(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate test data from version one to version two."""
    data["schema_version"] = 2
    data["migrations_applied"].append(1)
    return data


def migrate_two_to_three(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate test data from version two to version three."""
    data["schema_version"] = 3
    data["migrations_applied"].append(2)
    return data


def test_migration_manager_returns_current_data_unchanged() -> None:
    """Current resource data does not need a migration."""
    data = {
        "schema_version": 3,
        "value": "current",
        "migrations_applied": [],
    }
    manager = MigrationManager(VersionThreeModel, {})

    result = manager.migrate_resource(data)

    assert result == VersionThreeModel.model_validate(data)
    assert data == {
        "schema_version": 3,
        "value": "current",
        "migrations_applied": [],
    }


def test_migration_manager_applies_all_steps_without_mutating_input() -> None:
    """Migration steps run in order and do not mutate their input."""
    data = {
        "schema_version": 1,
        "value": "old",
        "migrations_applied": [],
    }
    manager = MigrationManager(
        VersionThreeModel,
        {
            1: migrate_one_to_two,
            2: migrate_two_to_three,
        },
    )

    result = manager.migrate_resource(data)

    assert result == VersionThreeModel(
        value="old",
        migrations_applied=[1, 2],
    )
    assert data["migrations_applied"] == []
    assert data["schema_version"] == 1


def test_migration_manager_treats_missing_version_as_version_one() -> None:
    """Legacy data without schema_version starts at version one."""
    data = {
        "value": "old",
        "migrations_applied": [],
    }
    manager = MigrationManager(
        VersionThreeModel,
        {
            1: migrate_one_to_two,
            2: migrate_two_to_three,
        },
    )

    result = manager.migrate_resource(data)

    assert result.schema_version == 3
    assert result.migrations_applied == [1, 2]
    assert "schema_version" not in data


def test_migration_manager_rejects_missing_step() -> None:
    """Every intermediate migration must be registered."""
    manager = MigrationManager(
        VersionThreeModel,
        {
            2: migrate_two_to_three,
        },
    )

    with pytest.raises(
        MigrationError,
        match="Missing VersionThreeModel migration from schema version 1 to 2",
    ):
        manager.migrate_resource(
            {
                "schema_version": 1,
                "value": "old",
                "migrations_applied": [],
            }
        )


def test_migration_manager_rejects_newer_schema() -> None:
    """Forward-only migration does not accept a newer resource schema."""
    manager = MigrationManager(VersionThreeModel, {})

    with pytest.raises(
        MigrationError,
        match=("VersionThreeModel schema version 4 is newer than supported version 3"),
    ):
        manager.migrate_resource(
            {
                "schema_version": 4,
                "value": "future",
                "migrations_applied": [],
            }
        )


@pytest.mark.parametrize("version", [True, 0, -1, 1.0, "1", None])
def test_migration_manager_rejects_invalid_schema_version(version: Any) -> None:
    """Schema versions must be positive integers."""
    manager = MigrationManager(VersionThreeModel, {})

    with pytest.raises(
        MigrationError, match="Schema version must be a positive integer"
    ):
        manager.migrate_resource(
            {
                "schema_version": version,
                "value": "invalid",
                "migrations_applied": [],
            }
        )


def test_migration_manager_rejects_wrong_step_version() -> None:
    """A migration must advance by exactly one version."""

    def skip_version(data: dict[str, Any]) -> dict[str, Any]:
        data["schema_version"] = 3
        return data

    manager = MigrationManager(
        VersionThreeModel,
        {
            1: skip_version,
            2: migrate_two_to_three,
        },
    )

    with pytest.raises(
        MigrationError,
        match="must set schema_version to 2, but set it to 3",
    ):
        manager.migrate_resource(
            {
                "schema_version": 1,
                "value": "old",
                "migrations_applied": [],
            }
        )


def test_migration_manager_wraps_step_error() -> None:
    """An error from a migration identifies the failed version step."""

    def failing_migration(data: dict[str, Any]) -> dict[str, Any]:
        raise KeyError("missing value")

    manager = MigrationManager(
        VersionThreeModel,
        {
            1: failing_migration,
            2: migrate_two_to_three,
        },
    )

    with pytest.raises(
        MigrationError,
        match=("VersionThreeModel migration from schema version 1 to 2 failed"),
    ) as error:
        manager.migrate_resource(
            {
                "schema_version": 1,
                "value": "old",
                "migrations_applied": [],
            }
        )
    assert "missing value" not in str(error.value)


def test_migration_manager_validates_final_data() -> None:
    """The result must validate against the current model."""

    def remove_required_value(data: dict[str, Any]) -> dict[str, Any]:
        data["schema_version"] = 2
        data.pop("value")
        return data

    manager = MigrationManager(
        VersionThreeModel,
        {
            1: remove_required_value,
            2: migrate_two_to_three,
        },
    )

    with pytest.raises(
        MigrationError,
        match=(
            "VersionThreeModel data does not validate against current schema version 3"
        ),
    ):
        manager.migrate_resource(
            {
                "schema_version": 1,
                "value": "old",
                "migrations_applied": [],
            }
        )


def test_migration_manager_requires_backup_for_unversioned_current_data() -> None:
    """Normalizing an unversioned resource preserves its original form."""
    manager = MigrationManager(VersionOneModel, {})

    assert manager.requires_backup({"value": "legacy"}) is True
    assert manager.requires_backup({"schema_version": 1, "value": "current"}) is False
    assert manager.migrate_resource({"value": "legacy"}).model_dump() == {
        "schema_version": 1,
        "value": "legacy",
    }


def test_migration_manager_requires_literal_schema_version() -> None:
    """Migratable models declare one literal current version."""

    class InvalidModel(BaseModel):
        schema_version: int = 1

    with pytest.raises(
        TypeError, match="InvalidModel.schema_version must use Literal\\[int\\]"
    ):
        MigrationManager(InvalidModel, {})


def test_migration_manager_requires_schema_version_field() -> None:
    """Migratable models must declare their current schema version."""

    class InvalidModel(BaseModel):
        value: str

    with pytest.raises(
        TypeError, match="InvalidModel must define a schema_version field"
    ):
        MigrationManager(InvalidModel, {})


def test_migration_manager_requires_one_literal_version() -> None:
    """Migratable models cannot accept more than one schema version."""

    class InvalidModel(BaseModel):
        schema_version: Literal[1, 2] = 2

    with pytest.raises(
        TypeError, match="InvalidModel.schema_version must contain one version"
    ):
        MigrationManager(InvalidModel, {})


def test_migration_manager_requires_current_version_default() -> None:
    """The schema version default must equal its literal version."""

    class InvalidModel(BaseModel):
        schema_version: Literal[2] = cast("Literal[2]", 1)

    with pytest.raises(
        TypeError, match="InvalidModel.schema_version must default to 2"
    ):
        MigrationManager(InvalidModel, {})


def test_migration_manager_rejects_invalid_declared_version() -> None:
    """Invalid model versions are configuration errors."""

    class InvalidModel(BaseModel):
        schema_version: Literal[0] = 0

    with pytest.raises(TypeError, match="Schema version must be a positive integer"):
        MigrationManager(InvalidModel, {})
