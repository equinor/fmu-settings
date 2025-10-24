"""Tests for the cache manager utilities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fmu.settings._resources.cache_manager import (
    _CACHEDIR_TAG_CONTENT,
    CacheManager,
)

if TYPE_CHECKING:
    import pytest

    from fmu.settings._fmu_dir import ProjectFMUDirectory


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
