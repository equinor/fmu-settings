"""The generic configuration file in a .fmu directory."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final, Self

from fmu.settings._logging import null_logger
from fmu.settings.models.project_config import ProjectConfig
from fmu.settings.models.user_config import UserConfig

from .pydantic_resource_manager import (
    MutablePydanticResourceManager,
)

if TYPE_CHECKING:
    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        ProjectFMUDirectory,
        UserFMUDirectory,
    )

logger: Final = null_logger(__name__)


class ProjectConfigManager(MutablePydanticResourceManager[ProjectConfig]):
    """Manages the .fmu configuration file in a project."""

    def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initializes the ProjectConfig resource manager."""
        super().__init__(fmu_dir, ProjectConfig)

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the config file."""
        return Path("config.json")


class UserConfigManager(MutablePydanticResourceManager[UserConfig]):
    """Manages the .fmu configuration file in a user's home directory."""

    def __init__(self: Self, fmu_dir: UserFMUDirectory) -> None:
        """Initializes the UserConfig resource manager."""
        super().__init__(fmu_dir, UserConfig)

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the config file."""
        return Path("config.json")
