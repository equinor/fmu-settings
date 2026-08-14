"""Integration tests for migrations in Pydantic resource managers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Self, cast
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from fmu.settings import MigrationError
from fmu.settings._migrations import MigrationManager
from fmu.settings._resources.lock_manager import LockManager
from fmu.settings._resources.pydantic_resource_manager import PydanticResourceManager
from fmu.settings.models.change_info import ChangeType
from fmu.settings.models.mappings import InternalMappings
from fmu.settings.models.project_config import ProjectConfig

if TYPE_CHECKING:
    from fmu.settings._fmu_dir import ProjectFMUDirectory


class VersionTwoResource(BaseModel):
    """Test-only resource model at schema version two."""

    schema_version: Literal[2] = 2
    value: str


class VersionOneResource(BaseModel):
    """Test-only resource model at schema version one."""

    schema_version: Literal[1] = 1
    value: str


def migrate_one_to_two(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate the test resource to schema version two."""
    data["schema_version"] = 2
    return data


class MigratableResourceManager(PydanticResourceManager[VersionTwoResource]):
    """Test manager with one registered migration."""

    def __init__(self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initialize the test manager."""
        super().__init__(
            fmu_dir,
            VersionTwoResource,
            migration_manager=MigrationManager(
                VersionTwoResource,
                {1: migrate_one_to_two},
            ),
        )

    @property
    def relative_path(self: Self) -> Path:
        """Return the test resource path."""
        return Path("migratable.json")


def test_load_migrates_in_memory_without_changing_disk(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Reading an old resource migrates only the in-memory representation."""
    manager = MigratableResourceManager(fmu_dir)
    old_content = json.dumps({"schema_version": 1, "value": "old"}, indent=2)
    fmu_dir.write_text_file(manager.relative_path, old_content)

    loaded = manager.load()

    assert loaded == VersionTwoResource(value="old")
    assert manager._cache == loaded
    assert fmu_dir.read_text_file(manager.relative_path) == old_content
    assert fmu_dir.cache.list_revisions(manager.relative_path) == []


def test_save_after_migration_backs_up_old_content(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """The first write backs up and caches the old data before writing current data."""
    manager = MigratableResourceManager(fmu_dir)
    old_content = json.dumps({"schema_version": 1, "value": "old"}, indent=2)
    fmu_dir.write_text_file(manager.relative_path, old_content)
    loaded = manager.load()

    manager.save(loaded.model_copy(update={"value": "updated"}))

    disk_data = json.loads(fmu_dir.read_text_file(manager.relative_path))
    assert disk_data == {"schema_version": 2, "value": "updated"}

    backup_directory = fmu_dir.get_file_path("migration-backups/migratable")
    backups = [path for path in backup_directory.iterdir() if path.is_file()]
    assert len(backups) == 1
    assert backups[0].name.endswith("-VersionTwoResource-v1.json")
    assert backups[0].read_text(encoding="utf-8") == old_content

    cached_data = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in fmu_dir.cache.list_revisions(manager.relative_path)
    ]
    assert {"schema_version": 1, "value": "old"} in cached_data
    assert {"schema_version": 2, "value": "updated"} in cached_data


def test_cached_version_one_content_can_be_read_and_restored(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Reading or restoring the revision migrates its content to version two."""
    manager = MigratableResourceManager(fmu_dir)
    old_content = json.dumps({"schema_version": 1, "value": "old"}, indent=2)
    fmu_dir.write_text_file(manager.relative_path, old_content)
    manager.save(VersionTwoResource(value="updated"))

    old_revision = next(
        path
        for path in fmu_dir.cache.list_revisions(manager.relative_path)
        if json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1
    )

    cached_model = fmu_dir.cache.get_revision_content(
        manager.relative_path,
        old_revision.name,
        manager.model_class,
        migration_manager=manager.migration_manager,
    )
    assert cached_model == VersionTwoResource(value="old")

    fmu_dir.cache.restore_revision(
        manager.relative_path,
        old_revision.name,
        manager.model_class,
        migration_manager=manager.migration_manager,
    )
    assert json.loads(fmu_dir.read_text_file(manager.relative_path)) == {
        "schema_version": 2,
        "value": "old",
    }


def test_cache_manager_cannot_read_content_from_a_newer_schema_version(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A version-two manager cannot read a cached version-three revision."""
    manager = MigratableResourceManager(fmu_dir)
    revision = fmu_dir.cache.store_revision(
        manager.relative_path,
        json.dumps({"schema_version": 3, "value": "future"}),
    )
    assert revision is not None

    with pytest.raises(
        MigrationError,
        match=(
            "Cannot migrate cached content for 'migratable.json'.*"
            "schema version 3, which is newer than supported version 2"
        ),
    ):
        fmu_dir.cache.get_revision_content(
            manager.relative_path,
            revision.name,
            manager.model_class,
            migration_manager=manager.migration_manager,
        )


def test_migration_save_respects_lock_before_backup(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A foreign lock prevents both migration backup and resource write."""
    manager = MigratableResourceManager(fmu_dir)
    old_content = json.dumps({"schema_version": 1, "value": "old"}, indent=2)
    fmu_dir.write_text_file(manager.relative_path, old_content)
    revisions_before = fmu_dir.cache.list_revisions(manager.relative_path)
    lock = LockManager(fmu_dir)

    with (
        patch("socket.gethostname", return_value="other-host"),
        patch("os.getpid", return_value=12345),
    ):
        lock.acquire()

    try:
        with pytest.raises(PermissionError, match="Cannot write to .fmu directory"):
            manager.save(VersionTwoResource(value="updated"))
    finally:
        with (
            patch("socket.gethostname", return_value="other-host"),
            patch("os.getpid", return_value=12345),
        ):
            lock.release()

    assert fmu_dir.read_text_file(manager.relative_path) == old_content
    assert fmu_dir.cache.list_revisions(manager.relative_path) == revisions_before


def test_save_continues_when_migration_backup_fails(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A failed migration backup does not block saving current data."""
    manager = MigratableResourceManager(fmu_dir)
    old_content = json.dumps({"schema_version": 1, "value": "old"}, indent=2)
    fmu_dir.write_text_file(manager.relative_path, old_content)
    original_write_text_file = fmu_dir.write_text_file

    def write_text_file(
        relative_path: Path | str,
        content: str,
        encoding: str = "utf-8",
    ) -> None:
        if Path(relative_path).parts[:1] == ("migration-backups",):
            raise OSError("backup unavailable")
        original_write_text_file(relative_path, content, encoding=encoding)

    with patch.object(fmu_dir, "write_text_file", side_effect=write_text_file):
        manager.save(VersionTwoResource(value="updated"))

    assert json.loads(fmu_dir.read_text_file(manager.relative_path)) == {
        "schema_version": 2,
        "value": "updated",
    }
    assert not fmu_dir.get_file_path("migration-backups").exists()


def test_current_schema_save_does_not_add_migration_backup(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A normal save stores only the existing post-write revision."""
    manager = MigratableResourceManager(fmu_dir)
    current = VersionTwoResource(value="current")
    fmu_dir.write_text_file(
        manager.relative_path,
        current.model_dump_json(by_alias=True, indent=2),
    )

    manager.save(current.model_copy(update={"value": "updated"}))

    revisions = fmu_dir.cache.list_revisions(manager.relative_path)
    assert len(revisions) == 1
    assert json.loads(revisions[0].read_text(encoding="utf-8")) == {
        "schema_version": 2,
        "value": "updated",
    }
    assert not fmu_dir.get_file_path("migration-backups").exists()


def test_save_overwrites_non_object_json_without_a_migration_backup(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Allow a valid save when the existing resource contains a JSON list.

    For example, the existing file contains only ``[]`` instead of the expected JSON
    object. The list has no schema version, so it cannot be migrated and is not
    saved as a migration backup. The valid version-two model replaces the list with
    ``{"schema_version": 2, "value": "current"}``, and only this replacement is
    added to the normal cache.
    """
    manager = MigratableResourceManager(fmu_dir)
    fmu_dir.write_text_file(manager.relative_path, json.dumps([]))

    manager.save(VersionTwoResource(value="current"))

    assert json.loads(fmu_dir.read_text_file(manager.relative_path)) == {
        "schema_version": 2,
        "value": "current",
    }
    revisions = fmu_dir.cache.list_revisions(manager.relative_path)
    assert len(revisions) == 1
    assert json.loads(revisions[0].read_text(encoding="utf-8")) == {
        "schema_version": 2,
        "value": "current",
    }
    assert not fmu_dir.get_file_path("migration-backups").exists()


def test_save_does_not_overwrite_a_newer_stored_version(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A version-two manager rejects version-three data before writing or caching."""
    manager = MigratableResourceManager(fmu_dir)
    future_content = json.dumps({"schema_version": 3, "value": "future"})
    fmu_dir.write_text_file(manager.relative_path, future_content)

    with pytest.raises(
        MigrationError,
        match=(
            "Failed to check migration requirements for resource file "
            "'MigratableResourceManager'.*"
            "schema version 3, which is newer than supported version 2"
        ),
    ):
        manager.save(VersionTwoResource(value="current"))

    assert fmu_dir.read_text_file(manager.relative_path) == future_content
    assert fmu_dir.cache.list_revisions(manager.relative_path) == []


def test_load_rejects_newer_schema(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A migration error identifies the resource that could not be loaded."""
    manager = MigratableResourceManager(fmu_dir)
    fmu_dir.write_text_file(
        manager.relative_path,
        json.dumps({"schema_version": 3, "value": "future"}),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Stored VersionTwoResource data has schema version 3, which is newer "
            "than supported version 2"
        ),
    ):
        manager.load()


def test_load_rejects_non_object_resource(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A migratable resource must contain a JSON object."""
    manager = MigratableResourceManager(fmu_dir)
    fmu_dir.write_text_file(manager.relative_path, json.dumps([]))

    with pytest.raises(
        ValueError,
        match="Stored VersionTwoResource data must be a JSON object",
    ):
        manager.load()


@pytest.mark.parametrize(
    ("directory_fixture", "resource_name"),
    [
        ("fmu_dir", "config"),
        ("fmu_dir", "mappings"),
        ("user_fmu_dir", "config"),
    ],
)
def test_resource_has_version_one_migration_manager(
    request: pytest.FixtureRequest,
    directory_fixture: str,
    resource_name: str,
) -> None:
    """Check the current schema version and migrations for each resource.

    Project config, user config, and mappings currently use schema version one, so
    their migration registries are empty. Update this test when a resource gets a
    new schema version and migration function.
    """
    fmu_directory = request.getfixturevalue(directory_fixture)
    manager = getattr(fmu_directory, resource_name).migration_manager

    assert manager is not None
    assert manager.current_version == 1
    assert manager.migrations == {}


def test_unversioned_project_config_can_be_read_and_restored_from_cache(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Legacy config restores version-one data, runtime settings, and changelog."""
    legacy_config = fmu_dir.config.load().model_dump(mode="json")
    legacy_config.pop("schema_version")
    legacy_config["cache_max_revisions"] = 7
    revision = fmu_dir.cache.store_revision(
        "config.json",
        json.dumps(legacy_config),
    )
    assert revision is not None

    cached = fmu_dir.get_cache_content("config.json", revision.name)
    assert isinstance(cached, ProjectConfig)
    assert cached.schema_version == 1
    assert cached.cache_max_revisions == 7  # noqa: PLR2004

    fmu_dir.restore_from_cache("config.json", revision.name)

    restored = fmu_dir.config.load()
    assert restored.schema_version == 1
    assert restored.cache_max_revisions == 7  # noqa: PLR2004
    assert fmu_dir.cache_max_revisions == 7  # noqa: PLR2004
    assert fmu_dir.changelog.load().root[-1].change_type == ChangeType.restore


def test_unversioned_mappings_can_be_read_and_restored_from_cache(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Legacy mappings restore as version one and add a changelog entry."""
    legacy_mappings = InternalMappings().model_dump(mode="json")
    legacy_mappings.pop("schema_version")
    revision = fmu_dir.cache.store_revision(
        "mappings.json",
        json.dumps(legacy_mappings),
    )
    assert revision is not None

    cached = fmu_dir.get_cache_content("mappings.json", revision.name)
    assert isinstance(cached, InternalMappings)
    assert cached.schema_version == 1

    fmu_dir.restore_from_cache("mappings.json", revision.name)

    assert fmu_dir.mappings.load() == InternalMappings()
    assert fmu_dir.changelog.load().root[-1].change_type == ChangeType.restore


def test_resource_manager_rejects_migration_functions_for_another_model(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """The migration and resource managers must use the same Pydantic model."""
    migration_manager = MigrationManager(
        VersionTwoResource,
        {1: migrate_one_to_two},
    )

    with pytest.raises(
        TypeError,
        match="Migration manager model must match the resource manager model",
    ):
        PydanticResourceManager[VersionOneResource](
            fmu_dir,
            VersionOneResource,
            migration_manager=cast(
                "MigrationManager[VersionOneResource]",
                migration_manager,
            ),
        )
