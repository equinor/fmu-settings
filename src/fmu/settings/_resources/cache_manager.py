"""Utilities for storing revision snapshots of .fmu files."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Final, Self
from uuid import uuid4

from fmu.settings._logging import null_logger

if TYPE_CHECKING:
    from fmu.settings._fmu_dir import FMUDirectoryBase

logger: Final = null_logger(__name__)

_CACHEDIR_TAG_CONTENT: Final = (
    "Signature: 8a477f597d28d172789f06886806bc55\n"
    "# This directory contains cached FMU files.\n"
    "# For information about cache directory tags, see:\n"
    "#	https://bford.info/cachedir/spec.html"
)


class CacheManager:
    """Stores complete file revisions under the `.fmu/cache` tree."""

    MIN_REVISIONS: ClassVar[int] = 5
    RETENTION_DAYS: ClassVar[int] = 30

    def __init__(
        self: Self,
        fmu_dir: FMUDirectoryBase,
        max_revisions: int = 5,
    ) -> None:
        """Initialize the cache manager.

        Args:
            fmu_dir: The FMUDirectory instance.
            max_revisions: Maximum number of revisions to retain. Default is 5.
                Values below 5 are set to 5.
        """
        self._fmu_dir = fmu_dir
        self._cache_root = Path("cache")
        self._max_revisions = max(self.MIN_REVISIONS, max_revisions)

    @property
    def max_revisions(self: Self) -> int:
        """Maximum number of revisions retained per resource."""
        return self._max_revisions

    @max_revisions.setter
    def max_revisions(self: Self, value: int) -> None:
        """Update the per-resource revision retention.

        Args:
            value: The new maximum number of revisions. Minimum value is 5.
                Values below 5 are set to 5.
        """
        self._max_revisions = max(self.MIN_REVISIONS, value)

    def store_revision(
        self: Self,
        resource_file_path: Path | str,
        content: str,
        encoding: str = "utf-8",
        skip_trim: bool = False,
    ) -> Path | None:
        """Write a full snapshot of the resource file to the cache directory.

        Args:
            resource_file_path: Relative path within the ``.fmu`` directory (e.g.,
                ``config.json``) of the resource file being cached.
            content: Serialized payload to store.
            encoding: Encoding used when persisting the snapshot. Defaults to UTF-8.
            skip_trim: If True, skip count-based trimming. Default is False.

        Returns:
            Absolute filesystem path to the stored snapshot.
        """
        resource_file_path = Path(resource_file_path)
        cache_dir = self._ensure_resource_cache_dir(resource_file_path)
        snapshot_name = self._snapshot_filename(resource_file_path)
        snapshot_path = cache_dir / snapshot_name

        cache_relative = self._cache_root / resource_file_path.stem
        self._fmu_dir.write_text_file(
            cache_relative / snapshot_name, content, encoding=encoding
        )
        logger.debug("Stored revision snapshot at %s", snapshot_path)

        if not skip_trim:
            self._trim(cache_dir)
        return snapshot_path

    def list_revisions(self: Self, resource_file_path: Path | str) -> list[Path]:
        """List existing snapshots for a resource file, sorted oldest to newest.

        Args:
            resource_file_path: Relative path within the ``.fmu`` directory (e.g.,
                ``config.json``) whose cache entries should be listed.

        Returns:
            A list of absolute `Path` objects sorted oldest to newest.
        """
        resource_file_path = Path(resource_file_path)
        cache_relative = self._cache_root / resource_file_path.stem
        if not self._fmu_dir.file_exists(cache_relative):
            return []
        cache_dir = self._fmu_dir.get_file_path(cache_relative)

        revisions = [p for p in cache_dir.iterdir() if p.is_file()]
        revisions.sort(key=lambda path: path.name)
        return revisions

    def _ensure_resource_cache_dir(self: Self, resource_file_path: Path) -> Path:
        """Create (if needed) and return the cache directory for resource file."""
        self._cache_root_path(create=True)
        resource_cache_dir_relative = self._cache_root / resource_file_path.stem
        return self._fmu_dir.ensure_directory(resource_cache_dir_relative)

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

    def _snapshot_filename(self: Self, resource_file_path: Path) -> str:
        """Generate a timestamped filename for the next snapshot."""
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        suffix = resource_file_path.suffix or ".txt"
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

    def trim_by_age(
        self: Self, resource_file_path: Path | str, retention_days: int | None = None
    ) -> None:
        """Remove snapshots older than retention_days.

        Args:
            resource_file_path: Relative path within the ``.fmu`` directory (e.g.,
                ``logs/user_session_log.json``) whose cache entries should be trimmed.
            retention_days: Maximum age in days to retain snapshots.
                If None, uses CacheManager.RETENTION_DAYS (default: 30 days).
        """
        if retention_days is None:
            retention_days = self.RETENTION_DAYS
        revisions = self.list_revisions(resource_file_path)
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)

        for revision in revisions:
            try:
                mtime_timestamp = revision.stat().st_mtime
                file_time = datetime.fromtimestamp(mtime_timestamp, tz=UTC)
            except (OSError, ValueError):
                logger.warning("Skipping file with unreadable mtime: %s", revision.name)
                continue

            if file_time < cutoff:
                revision.unlink()
                logger.debug("Deleted old revision: %s", revision)
