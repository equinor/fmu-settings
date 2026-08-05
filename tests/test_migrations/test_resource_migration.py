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
    from fmu.settings._fmu_dir import ProjectFMUDirectory, UserFMUDirectory


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
    """The first write backs up old data outside the normal cache."""
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
    assert {"schema_version": 1, "value": "old"} not in cached_data
    assert {"schema_version": 2, "value": "updated"} in cached_data


def test_cached_old_schema_is_readable_and_restorable(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Existing cache APIs migrate an old backup before using its content."""
    manager = MigratableResourceManager(fmu_dir)
    old_content = json.dumps({"schema_version": 1, "value": "old"}, indent=2)
    fmu_dir.write_text_file(manager.relative_path, old_content)
    old_revision = fmu_dir.cache.store_revision(manager.relative_path, old_content)
    assert old_revision is not None
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


def test_cache_read_rejects_newer_schema_with_resource_context(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A cache migration error identifies the affected resource."""
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
            "schema version 3 is newer than supported version 2"
        ),
    ):
        fmu_dir.cache.get_revision_content(
            manager.relative_path,
            revision.name,
            manager.model_class,
            migration_manager=manager.migration_manager,
        )


def test_force_load_without_store_cache_preserves_existing_cached_model(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A forced migrated read can avoid replacing the in-memory cache."""
    manager = MigratableResourceManager(fmu_dir)
    fmu_dir.write_text_file(
        manager.relative_path,
        json.dumps({"schema_version": 1, "value": "first"}),
    )
    cached = manager.load()
    fmu_dir.write_text_file(
        manager.relative_path,
        json.dumps({"schema_version": 1, "value": "second"}),
    )

    reloaded = manager.load(force=True, store_cache=False)

    assert reloaded == VersionTwoResource(value="second")
    assert manager._cache == cached


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


def test_save_replaces_non_object_json_without_migration_backup(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A valid model can replace non-object JSON without preserving it."""
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


def test_save_rejects_newer_stored_schema_before_overwrite(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A save does not overwrite stored data from a newer schema."""
    manager = MigratableResourceManager(fmu_dir)
    future_content = json.dumps({"schema_version": 3, "value": "future"})
    fmu_dir.write_text_file(manager.relative_path, future_content)

    with pytest.raises(
        MigrationError,
        match=(
            "Failed to check migration requirements for resource file "
            "'MigratableResourceManager'.*"
            "schema version 3 is newer than supported version 2"
        ),
    ):
        manager.save(VersionTwoResource(value="current"))

    assert fmu_dir.read_text_file(manager.relative_path) == future_content
    assert fmu_dir.cache.list_revisions(manager.relative_path) == []


def test_load_rejects_newer_schema_with_resource_context(
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
            "Failed to migrate resource file for 'MigratableResourceManager'.*"
            "schema version 3 is newer than supported version 2"
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
        match=(
            "Failed to migrate resource file for 'MigratableResourceManager'.*"
            "VersionTwoResource resource must be a JSON object"
        ),
    ):
        manager.load()


def test_project_resource_managers_have_version_one_migration_managers(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Project resources are wired without a dummy version two."""
    managers = [
        fmu_dir.config.migration_manager,
        fmu_dir.mappings.migration_manager,
    ]

    assert all(manager is not None for manager in managers)
    assert all(manager.current_version == 1 for manager in managers if manager)
    assert all(manager.migrations == {} for manager in managers if manager)


def test_user_config_has_version_one_migration_manager(
    user_fmu_dir: UserFMUDirectory,
) -> None:
    """User config is wired without a dummy version two."""
    manager = user_fmu_dir.config.migration_manager

    assert manager is not None
    assert manager.current_version == 1
    assert manager.migrations == {}


def test_project_config_cache_boundary_handles_unversioned_revision(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Project cache APIs normalize and restore an unversioned config revision."""
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


def test_mappings_cache_boundary_handles_unversioned_revision(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Project cache APIs use the mappings migration manager across the union."""
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


def test_resource_manager_rejects_mismatched_migration_model(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A resource manager cannot use migrations for a different model."""
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


def test_cache_manager_rejects_mismatched_migration_model(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Cache validation cannot return a model different from its annotation."""
    revision = fmu_dir.cache.store_revision(
        "version-one.json",
        VersionOneResource(value="current").model_dump_json(),
    )
    assert revision is not None
    migration_manager = MigrationManager(
        VersionTwoResource,
        {1: migrate_one_to_two},
    )

    with pytest.raises(
        TypeError,
        match="Migration manager model must match the requested model",
    ):
        fmu_dir.cache.get_revision_content(
            "version-one.json",
            revision.name,
            VersionOneResource,
            migration_manager=cast(
                "MigrationManager[VersionOneResource]",
                migration_manager,
            ),
        )
