"""Manages an .fmu eventlog file."""

from __future__ import annotations

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


class EventlogManager(LogManager[EventInfo]):
    """Manages the .fmu changelog file."""

    def __init__(self: Self, fmu_dir: FMUDirectoryBase) -> None:
        """Initializes the Event log resource manager."""
        super().__init__(fmu_dir, Log[EventInfo])

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the log file."""
        return Path("logs") / LogFileName.eventlog
