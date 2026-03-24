"""Tests for the cache manager utilities."""

import json
import os
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.cache_manager import (
    _CACHEDIR_TAG_CONTENT,
    CacheManager,
)
from fmu.settings.models.project_config import ProjectConfig


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


def test_cache_manager_list_revisions_permission_error(
    fmu_dir: ProjectFMUDirectory,
    no_permissions: Callable[[str | Path], AbstractContextManager[None]],
) -> None:
    """Listing revisions preserves permission errors on resource cache dirs."""
    manager = CacheManager(fmu_dir)
    manager.store_revision("foo.json", "one")

    with no_permissions(fmu_dir.path / "cache" / "foo"), pytest.raises(PermissionError):
        manager.list_revisions("foo.json")


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
    expected_snapshot_count = 5
    for i in range(expected_snapshot_count):
        manager.store_revision("foo.json", f"content_{i}", skip_trim=True)

    config_cache = fmu_dir.path / "cache" / "foo"
    snapshots = _read_snapshot_names(config_cache)
    assert len(snapshots) == expected_snapshot_count


def test_cache_manager_trim_all_revisions_prunes_only_over_limit_resources(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """trim_all_revisions prunes only resource caches exceeding the limit."""
    expected_snapshot_count = 5
    manager = CacheManager(fmu_dir, max_revisions=expected_snapshot_count)
    for i in range(7):
        manager.store_revision("foo.json", f"foo_{i}", skip_trim=True)
    for i in range(expected_snapshot_count):
        manager.store_revision("bar.json", f"bar_{i}", skip_trim=True)

    manager.trim_all_revisions()

    foo_cache = fmu_dir.path / "cache" / "foo"
    bar_cache = fmu_dir.path / "cache" / "bar"
    assert len(_read_snapshot_names(foo_cache)) == expected_snapshot_count
    assert len(_read_snapshot_names(bar_cache)) == expected_snapshot_count


def test_cache_manager_trim_all_revisions_ignores_non_directory_entries(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """trim_all_revisions skips files in the cache root."""
    expected_snapshot_count = 5
    manager = CacheManager(fmu_dir, max_revisions=expected_snapshot_count)
    for i in range(expected_snapshot_count + 2):
        manager.store_revision("foo.json", f"foo_{i}", skip_trim=True)

    cache_root = fmu_dir.path / "cache"
    cachedir_tag = cache_root / "CACHEDIR.TAG"
    assert cachedir_tag.read_text(encoding="utf-8") == _CACHEDIR_TAG_CONTENT

    manager.trim_all_revisions()

    foo_cache = cache_root / "foo"
    assert len(_read_snapshot_names(foo_cache)) == expected_snapshot_count
    assert cachedir_tag.read_text(encoding="utf-8") == _CACHEDIR_TAG_CONTENT


def test_cache_manager_trim_all_revisions_without_cache_directory(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """trim_all_revisions handles a missing cache directory gracefully."""
    manager = CacheManager(fmu_dir)
    manager.trim_all_revisions()


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


def test_cache_manager_get_revision_content_returns_model(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """get_revision_content returns a validated model instance."""
    manager = CacheManager(fmu_dir)
    cached_model = fmu_dir.config.load().model_copy(update={"version": "1.2.3"})
    snapshot = manager.store_revision(
        "config.json",
        cached_model.model_dump_json(by_alias=True, indent=2),
    )
    assert snapshot is not None

    restored = manager.get_revision_content(
        "config.json",
        snapshot.name,
        ProjectConfig,
    )

    assert restored.model_dump() == cached_model.model_dump()


def test_cache_manager_get_revision_content_raises_for_missing_revision(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Missing cache revisions raise FileNotFoundError."""
    manager = CacheManager(fmu_dir)
    with pytest.raises(
        FileNotFoundError,
        match="Cache revision 'missing.json' not found for resource 'config.json'",
    ):
        manager.get_revision_content("config.json", "missing.json", ProjectConfig)


def test_cache_manager_get_revision_content_raises_for_invalid_content(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Invalid cached JSON raises ValueError."""
    manager = CacheManager(fmu_dir)
    snapshot = manager.store_revision("config.json", "not json")
    assert snapshot is not None

    with pytest.raises(ValueError, match="Invalid cached content for 'config.json'"):
        manager.get_revision_content("config.json", snapshot.name, ProjectConfig)


def test_cache_manager_restore_revision_overwrites_and_caches_current(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """restore_revision replaces the resource and preserves the current state."""
    manager = CacheManager(fmu_dir)

    cached_model = fmu_dir.config.load().model_copy(update={"version": "1.2.3"})
    snapshot = manager.store_revision(
        "config.json",
        cached_model.model_dump_json(by_alias=True, indent=2),
    )
    assert snapshot is not None

    current_model = cached_model.model_copy(update={"version": "2.3.4"})
    current_json = current_model.model_dump_json(by_alias=True, indent=2)
    fmu_dir.write_text_file("config.json", current_json)

    pre_restore = manager.list_revisions("config.json")

    manager.restore_revision("config.json", snapshot.name, ProjectConfig)

    post_restore = manager.list_revisions("config.json")
    assert len(post_restore) == len(pre_restore) + 1

    restored_payload = json.loads(fmu_dir.read_text_file("config.json"))
    assert restored_payload["version"] == "1.2.3"

    cached_versions = [
        json.loads(path.read_text(encoding="utf-8"))["version"]
        for path in post_restore
        if path.suffix == ".json"
    ]
    assert "2.3.4" in cached_versions


def test_cache_manager_restore_revision_skips_invalid_current_state_cache(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that restore_revision does not cache invalid current state."""
    manager = CacheManager(fmu_dir)

    cached_model = fmu_dir.config.load().model_copy(update={"version": "1.2.3"})
    snapshot = manager.store_revision(
        "config.json",
        cached_model.model_dump_json(by_alias=True, indent=2),
    )
    assert snapshot is not None

    fmu_dir.write_text_file("config.json", "invalid json")

    pre_restore = manager.list_revisions("config.json")
    pre_restore_names = [path.name for path in pre_restore]

    manager.restore_revision("config.json", snapshot.name, ProjectConfig)

    post_restore = manager.list_revisions("config.json")
    post_restore_names = [path.name for path in post_restore]
    assert post_restore_names == pre_restore_names
    assert snapshot.name in post_restore_names

    restored_payload = json.loads(fmu_dir.read_text_file("config.json"))
    assert restored_payload["version"] == "1.2.3"
