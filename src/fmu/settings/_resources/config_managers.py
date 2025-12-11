"""The generic configuration file in a .fmu directory."""

from __future__ import annotations

import getpass
from datetime import UTC, datetime
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

    @property
    def diff_ignore_fields(self: Self) -> list[str]:
        """Returns a list of all config fields that should be ignored in a diff."""
        return ["created_at", "created_by", "last_modified_at", "last_modified_by"]

    def save(self: Self, model: ProjectConfig) -> None:
        """Save the ProjectConfig to disk, updating last_modified fields."""
        model_dict = model.model_dump()
        model_dict["last_modified_at"] = datetime.now(UTC)
        model_dict["last_modified_by"] = getpass.getuser()
        updated_model = ProjectConfig.model_validate(model_dict)
        super().save(updated_model)


class UserConfigManager(MutablePydanticResourceManager[UserConfig]):
    """Manages the .fmu configuration file in a user's home directory."""

    def __init__(self: Self, fmu_dir: UserFMUDirectory) -> None:
        """Initializes the UserConfig resource manager."""
        super().__init__(fmu_dir, UserConfig)

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the config file."""
        return Path("config.json")

    def save(self: Self, model: UserConfig) -> None:
        """Save the UserConfig to disk, updating last_modified_at."""
        model_dict = model.model_dump()
        model_dict["last_modified_at"] = datetime.now(UTC)
        updated_model = UserConfig.model_validate(model_dict)
        super().save(updated_model)
