"""Tests for the cache manager utilities."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.cache_manager import (
    _CACHEDIR_TAG_CONTENT,
    CacheManager,
)


def _read_snapshot_names(config_cache: Path) -> list[str]:
    return sorted(p.name for p in config_cache.iterdir() if p.is_file())


def test_cache_manager_list_revisions_without_directory(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Listing revisions on a missing cache dir yields an empty list."""
    manager = CacheManager(fmu_dir)
    assert manager.list_revisions("foo.json") == []


def test_cache_manager_list_revisions_with_existing_snapshots(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Listing revisions returns sorted snapshot paths."""
    manager = CacheManager(fmu_dir)
    manager.store_revision("foo.json", "one")
    manager.store_revision("foo.json", "two")
    revisions = manager.list_revisions("foo.json")
    assert [path.name for path in revisions] == sorted(path.name for path in revisions)
    assert len(revisions) == 2  # noqa: PLR2004


def test_cache_manager_honours_existing_cachedir_tag(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Existing cachedir tags are preserved when storing revisions."""
    cache_root = fmu_dir.path / "cache"
    cache_root.mkdir(exist_ok=True)
    tag_path = cache_root / "CACHEDIR.TAG"
    tag_path.write_text("custom tag", encoding="utf-8")

    manager = CacheManager(fmu_dir)
    manager.store_revision("foo.json", '{"foo": "bar"}')

    assert tag_path.read_text(encoding="utf-8") == "custom tag"


def test_cache_manager_cache_root_helpers_create_tag(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Cache root helpers return consistent paths and create cachedir tags."""
    manager = CacheManager(fmu_dir)
    root = manager._cache_root_path(create=False)
    assert root == fmu_dir.get_file_path("cache")

    created = manager._cache_root_path(create=True)
    assert created == root

    tag_path = created / "CACHEDIR.TAG"
    assert tag_path.is_file()
    assert tag_path.read_text(encoding="utf-8") == _CACHEDIR_TAG_CONTENT


def test_cache_manager_uses_default_extension_for_suffixless_paths(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Files without suffix get '.txt' snapshots."""
    manager = CacheManager(fmu_dir)
    snapshot = manager.store_revision("logs/entry", "payload")
    assert snapshot is not None
    assert snapshot.suffix == ".txt"
    assert snapshot.read_text(encoding="utf-8") == "payload"


def test_cache_manager_trim_handles_missing_files(
    fmu_dir: ProjectFMUDirectory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trimming gracefully handles concurrent removals."""
    manager = CacheManager(fmu_dir, max_revisions=CacheManager.MIN_REVISIONS)
    for i in range(CacheManager.MIN_REVISIONS + 2):
        manager.store_revision("foo.json", f"content_{i}")

    original_unlink = Path.unlink

    def flaky_unlink(self: Path, *, missing_ok: bool = False) -> None:
        if self.name.endswith(".json") and not getattr(flaky_unlink, "raised", False):
            flaky_unlink.raised = True  # type: ignore[attr-defined]
            original_unlink(self, missing_ok=missing_ok)
            raise FileNotFoundError
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    manager.store_revision("foo.json", "final")

    config_cache = fmu_dir.path / "cache" / "foo"
    assert len(_read_snapshot_names(config_cache)) == CacheManager.MIN_REVISIONS


def test_cache_manager_skip_trim_parameter(fmu_dir: ProjectFMUDirectory) -> None:
    """store_revision with skip_trim=True does not enforce count-based limit."""
    manager = CacheManager(fmu_dir, max_revisions=3)
    for i in range(5):
        manager.store_revision("foo.json", f"content_{i}", skip_trim=True)

    config_cache = fmu_dir.path / "cache" / "foo"
    snapshots = _read_snapshot_names(config_cache)
    assert len(snapshots) == 5  # noqa: PLR2004


def test_cache_manager_trim_by_age_removes_old_files(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """trim_by_age removes snapshots older than retention_days."""
    manager = CacheManager(fmu_dir)
    config_cache = fmu_dir.path / "cache" / "foo"
    config_cache.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    old_time = now - timedelta(days=35)
    recent_time = now - timedelta(days=10)

    old_filename = old_time.strftime("%Y%m%dT%H%M%S.%fZ") + "-abc12345.json"
    recent_filename = recent_time.strftime("%Y%m%dT%H%M%S.%fZ") + "-def67890.json"

    old_file = config_cache / old_filename
    recent_file = config_cache / recent_filename
    old_file.write_text("old content", encoding="utf-8")
    recent_file.write_text("recent content", encoding="utf-8")
    old_mtime = old_time.timestamp()
    recent_mtime = recent_time.timestamp()
    os.utime(old_file, (old_mtime, old_mtime))
    os.utime(recent_file, (recent_mtime, recent_mtime))

    manager.trim_by_age("foo.json", retention_days=30)

    remaining = _read_snapshot_names(config_cache)
    assert len(remaining) == 1
    assert remaining[0] == recent_filename


def test_cache_manager_trim_by_age_uses_default_retention(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """trim_by_age uses RETENTION_DAYS when retention_days is None."""
    manager = CacheManager(fmu_dir)
    config_cache = fmu_dir.path / "cache" / "foo"
    config_cache.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    old_time = now - timedelta(days=CacheManager.RETENTION_DAYS + 5)
    recent_time = now - timedelta(days=10)

    old_filename = old_time.strftime("%Y%m%dT%H%M%S.%fZ") + "-abc12345.json"
    recent_filename = recent_time.strftime("%Y%m%dT%H%M%S.%fZ") + "-def67890.json"

    old_file = config_cache / old_filename
    recent_file = config_cache / recent_filename
    old_file.write_text("old content", encoding="utf-8")
    recent_file.write_text("recent content", encoding="utf-8")
    old_mtime = old_time.timestamp()
    recent_mtime = recent_time.timestamp()
    os.utime(old_file, (old_mtime, old_mtime))
    os.utime(recent_file, (recent_mtime, recent_mtime))

    manager.trim_by_age("foo.json")

    remaining = _read_snapshot_names(config_cache)
    assert len(remaining) == 1
    assert remaining[0] == recent_filename


def test_cache_manager_trim_by_age_skips_malformed_files(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """trim_by_age skips files with unexpected format."""
    manager = CacheManager(fmu_dir)
    config_cache = fmu_dir.path / "cache" / "foo"
    config_cache.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    old_time = now - timedelta(days=35)
    old_filename = old_time.strftime("%Y%m%dT%H%M%S.%fZ") + "-abc12345.json"
    malformed_filename = "malformed_file.json"

    old_file = config_cache / old_filename
    malformed_file = config_cache / malformed_filename
    old_file.write_text("old content", encoding="utf-8")
    malformed_file.write_text("malformed", encoding="utf-8")
    old_mtime = old_time.timestamp()
    os.utime(old_file, (old_mtime, old_mtime))

    manager.trim_by_age("foo.json", retention_days=30)

    remaining = _read_snapshot_names(config_cache)
    assert len(remaining) == 1
    assert remaining[0] == malformed_filename


def test_cache_manager_trim_by_age_no_cache_directory(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """trim_by_age handles missing cache directory gracefully."""
    manager = CacheManager(fmu_dir)
    manager.trim_by_age("foo.json", retention_days=30)
