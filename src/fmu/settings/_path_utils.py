"""Utilities for path checks that only hide missing-path errors."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def path_exists(path: Path) -> bool:
    """Return whether a path exists without masking other OS errors."""
    try:
        path.stat()
    except (FileNotFoundError, NotADirectoryError):
        return False
    return True


def path_is_dir(path: Path) -> bool:
    """Return whether a path is a directory without masking other OS errors."""
    try:
        return stat.S_ISDIR(path.stat().st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False


def path_is_file(path: Path) -> bool:
    """Return whether a path is a file without masking other OS errors."""
    try:
        return stat.S_ISREG(path.stat().st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False
