"""Models related to locking a .fmu directory against writes."""

from pydantic import BaseModel, Field

from fmu.settings import __version__
from fmu.settings.types import VersionStr


class LockInfo(BaseModel):
    """Represents a .fmu directory lock file."""

    pid: int
    """Process ID of the lock holder."""

    hostname: str
    """Hostname where the lock was acquired."""

    user: str
    """User who acquired the lock."""

    acquired_at: float
    """Unix timestamp when lock was acquired."""

    expires_at: float
    """Unix timestamp when lock expires."""

    version: VersionStr = Field(default=__version__)
    """The fmu-settings version acquiring the lock.

    Used for debugging."""
