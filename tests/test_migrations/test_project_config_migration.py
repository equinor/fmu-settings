"""Tests for migration of RMS paths in project config."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from fmu.settings import MigrationError, ProjectFMUDirectory


@pytest.mark.parametrize("schema_version", [None, 1])
@pytest.mark.parametrize(
    "path",
    [
        "/master/revision/rms/model/main.rms",
        "/master/rms/archive/revision/rms/model/main.rms",
        "rms/model/main.rms",
        None,
    ],
)
def test_load_project_config_migrates_rms_path(
    fmu_dir: ProjectFMUDirectory, schema_version: int | None, path: str | None
) -> None:
    """Read absolute paths as relative paths without requiring write access."""
    data = fmu_dir.config.load().model_dump(mode="json")
    data.pop("schema_version")
    if schema_version is not None:
        data["schema_version"] = schema_version
    data["rms"] = {"path": path, "version": "14.2.2"} if path else None
    original = json.dumps(data)
    fmu_dir.config.path.write_text(original)

    with patch.object(fmu_dir._lock, "ensure_can_write", side_effect=PermissionError):
        config = fmu_dir.config.load(force=True)
    assert config.schema_version == 2
    if path:
        assert config.rms is not None
        assert config.rms.path == Path("rms/model/main.rms")
    else:
        assert config.rms is None
    assert fmu_dir.config.path.read_text() == original


def test_save_migrated_project_config(fmu_dir: ProjectFMUDirectory) -> None:
    """Save the migrated relative RMS path and back up the original config."""
    data = fmu_dir.config.load().model_dump(mode="json")
    data["schema_version"] = 1
    data["rms"] = {"path": "/master/rms/model/main.rms", "version": "14.2.2"}
    original = json.dumps(data)
    fmu_dir.config.path.write_text(original)

    # Loading migrates the absolute RMS path in memory.
    migrated_config = fmu_dir.config.load(force=True)

    # Saving the migrated config writes the relative path to config.json.
    fmu_dir.config.save(migrated_config)

    # Verify that the migrated rel path is saved and the original config is backed up.
    saved = json.loads(fmu_dir.config.path.read_text())
    assert saved["schema_version"] == 2
    assert saved["rms"]["path"] == "rms/model/main.rms"
    backups = list((fmu_dir.path / "migration-backups/config").iterdir())
    assert len(backups) == 1
    assert backups[0].read_text() == original


def test_restore_project_config_migrates_absolute_rms_path(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Write a relative RMS path when restoring a version-one cache revision."""
    data = fmu_dir.config.load().model_dump(mode="json")
    data["schema_version"] = 1
    data["rms"] = {"path": "/master/rms/model/main.rms", "version": "14.2.2"}
    old_revision = fmu_dir.cache.store_revision(Path("config.json"), json.dumps(data))
    assert old_revision is not None

    fmu_dir.restore_from_cache(Path("config.json"), old_revision.name)

    restored = json.loads(fmu_dir.config.path.read_text())
    assert restored["schema_version"] == 2
    assert restored["rms"]["path"] == "rms/model/main.rms"


@pytest.mark.parametrize("path", ["/other/main.rms", "/master/rms/model"])
def test_project_config_migration_rejects_unrecognized_paths(
    fmu_dir: ProjectFMUDirectory, path: str
) -> None:
    """Reject absolute paths that cannot be converted without guessing."""
    data = fmu_dir.config.load().model_dump(mode="json")
    data["schema_version"] = 1
    data["rms"] = {"path": path, "version": "14.2.2"}
    fmu_dir.config.path.write_text(json.dumps(data))
    with pytest.raises(MigrationError) as error:
        fmu_dir.config.load(force=True)
    assert error.value.__cause__ is not None
    assert str(error.value.__cause__) == (
        f"Cannot migrate RMS path '{path}'. "
        "Expected an absolute path ending in 'rms/model/<project>'."
    )


def test_project_config_migration_rejects_invalid_rms_path_type(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Reject an RMS path with an unsupported type."""
    data = fmu_dir.config.load().model_dump(mode="json")
    data["schema_version"] = 1
    data["rms"] = {"path": 67, "version": "14.2.2"}
    fmu_dir.config.path.write_text(json.dumps(data))

    with pytest.raises(MigrationError):
        fmu_dir.config.load(force=True)
