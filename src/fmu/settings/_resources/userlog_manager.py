"""Manages an .fmu eventlog file."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Self

from fmu.settings._resources.log_manager import LogManager
from fmu.settings.models.log import Log, LogFileName
from fmu.settings.models.user_info import UserInfo

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        FMUDirectoryBase,
    )


class UserlogManager(LogManager[UserInfo]):
    """Manages the .fmu userlog file."""

    def __init__(self: Self, fmu_dir: FMUDirectoryBase) -> None:
        """Initializes the User log resource manager."""
        super().__init__(fmu_dir, Log[UserInfo])

        # If eventlog.json exists from previous session, cache it and then delete it
        # We want a fresh log each time
        if self.exists:
            content = self.fmu_dir.read_text_file(self.relative_path)
            self.fmu_dir.cache.store_revision(self.relative_path, content)
            self.path.unlink()

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the log file."""
        return Path("logs") / LogFileName.eventlog
