"""Manages an .fmu user_session_log file."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Self

from fmu.settings._resources.log_manager import LogManager
from fmu.settings.models.event_info import EventInfo
from fmu.settings.models.log import Log, LogFileName

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )


class UserSessionLogManager(LogManager[EventInfo]):
    """Manages the .fmu user session log file."""

    def __init__(
        self: Self, fmu_dir: FMUDirectoryBase, retention_days: int | None = None
    ) -> None:
        """Initializes the User session log resource manager."""
        super().__init__(fmu_dir, Log[EventInfo])

        # If user_session_log.json exists from previous session, cache it and delete
        # We want a fresh log each time
        if self.exists:
            self.fmu_dir._lock.ensure_can_write()
            content = self.fmu_dir.read_text_file(self.relative_path)
            self.fmu_dir.cache.store_revision(
                self.relative_path, content, skip_trim=True
            )
            with contextlib.suppress(FileNotFoundError):
                self.path.unlink()

        self.fmu_dir.cache.trim_by_age(
            self.relative_path, retention_days or self.fmu_dir.cache.RETENTION_DAYS
        )

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the log file."""
        return Path("logs") / LogFileName.user_session_log
