"""Utilities for storing revision snapshots of .fmu config files."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final, Self
from uuid import uuid4

from fmu.settings._logging import null_logger

if TYPE_CHECKING:
    from fmu.settings._fmu_dir import FMUDirectoryBase

logger: Final = null_logger(__name__)

_CACHEDIR_TAG_CONTENT: Final = (
    "Signature: 8a477f597d28d172789f06886806bc55\n"
    "# This directory contains cached FMU config files.\n"
    "# For information about cache directory tags, see:\n"
    "#	https://bford.info/cachedir/spec.html"
)


class CacheManager:
    """Stores complete file revisions under the `.fmu/cache` tree."""

    def __init__(
        self: Self,
        fmu_dir: FMUDirectoryBase,
        cache_root: str | Path = "cache",
        max_revisions: int = 5,
    ) -> None:
        """Initialize the cache manager.

        Args:
            fmu_dir: The FMUDirectory instance.
            cache_root: Relative path (within the ``.fmu`` directory) where snapshots
                are stored. Default is ``"cache"``.
            max_revisions: Maximum number of revisions to retain.
        """
        if Path(cache_root).is_absolute():
            raise ValueError("cache_root must be a path relative to the .fmu directory")

        self._fmu_dir = fmu_dir
        self._cache_root = Path(cache_root)
        self.max_revisions = max(0, max_revisions)

    def store_revision(
        self: Self, config_file_path: Path | str, content: str, encoding: str = "utf-8"
    ) -> Path | None:
        """Write a full snapshot of the config.json to the cache directory.

        Args:
            config_file_path: Relative path within the ``.fmu`` directory (e.g.,
                ``config.json``) of the config file being cached.
            content: Serialized payload to store.
            encoding: Encoding used when persisting the snapshot. Defaults to UTF-8.

        Returns:
            Absolute filesystem path to the stored snapshot, or ``None`` if caching is
            disabled (``max_revisions`` equals zero).
        """
        if self.max_revisions == 0:
            return None

        config_file_path = Path(config_file_path)
        cache_dir = self._ensure_config_cache_dir(config_file_path)
        snapshot_name = self._snapshot_filename(config_file_path)
        snapshot_path = cache_dir / snapshot_name

        cache_relative = self._cache_root / config_file_path.stem
        self._fmu_dir.write_text_file(
            cache_relative / snapshot_name, content, encoding=encoding
        )
        logger.debug("Stored revision snapshot at %s", snapshot_path)

        self._trim(cache_dir)
        return snapshot_path

    def list_revisions(self: Self, config_file_path: Path | str) -> list[Path]:
        """List existing snapshots for a config file, sorted oldest to newest.

        Args:
            config_file_path: Relative path within the ``.fmu`` directory (e.g.,
                ``config.json``) whose cache entries should be listed.

        Returns:
            A list of absolute `Path` objects sorted lexicographically (oldest first).
        """
        config_file_path = Path(config_file_path)
        config_cache_path = self._cache_root / config_file_path.stem
        if not self._fmu_dir.file_exists(config_cache_path):
            return []
        cache_dir = self._fmu_dir.get_file_path(config_cache_path)

        revisions = [p for p in cache_dir.iterdir() if p.is_file()]
        revisions.sort(key=lambda path: path.name)
        return revisions

    def _ensure_config_cache_dir(self: Self, config_file_path: Path) -> Path:
        """Create (if needed) and return the cache directory for config file."""
        self._cache_root_path(create=True)
        config_cache_dir_relative = self._cache_root / config_file_path.stem
        return self._fmu_dir.ensure_directory(config_cache_dir_relative)

    def _cache_root_path(self: Self, create: bool) -> Path:
        """Resolve the cache root, creating it and the cachedir tag if requested."""
        if create:
            cache_root = self._fmu_dir.ensure_directory(self._cache_root)
            self._ensure_cachedir_tag()
            return cache_root

        return self._fmu_dir.get_file_path(self._cache_root)

    def _ensure_cachedir_tag(self: Self) -> None:
        """Ensure the cache root complies with the Cachedir specification."""
        tag_path_relative = self._cache_root / "CACHEDIR.TAG"
        if self._fmu_dir.file_exists(tag_path_relative):
            return
        self._fmu_dir.write_text_file(tag_path_relative, _CACHEDIR_TAG_CONTENT)

    def _snapshot_filename(self: Self, config_file_path: Path) -> str:
        """Generate a timestamped filename for the next snapshot."""
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        suffix = config_file_path.suffix or ".txt"
        token = uuid4().hex[:8]
        return f"{timestamp}-{token}{suffix}"

    def _trim(self: Self, cache_dir: Path) -> None:
        """Remove the oldest snapshots until the retention limit is respected."""
        revisions = [p for p in cache_dir.iterdir() if p.is_file()]
        if len(revisions) <= self.max_revisions:
            return

        revisions.sort(key=lambda path: path.name)
        excess = len(revisions) - self.max_revisions
        for old_revision in revisions[:excess]:
            try:
                old_revision.unlink()
            except FileNotFoundError:
                continue
