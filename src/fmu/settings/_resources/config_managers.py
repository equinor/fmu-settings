"""The generic configuration file in a .fmu directory."""

from __future__ import annotations

import getpass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Self

from fmu.settings._logging import null_logger
from fmu.settings._migrations import MigrationManager
from fmu.settings._migrations.project_config import PROJECT_CONFIG_MIGRATIONS
from fmu.settings._migrations.user_config import USER_CONFIG_MIGRATIONS
from fmu.settings.models.project_config import ProjectConfig
from fmu.settings.models.user_config import UserConfig

from .pydantic_resource_manager import (
    MutablePydanticResourceManager,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    # Avoid circular dependency for type hint in __init__ only
    from fmu.settings._fmu_dir import (
        ProjectFMUDirectory,
        UserFMUDirectory,
    )

logger: Final = null_logger(__name__)


class ProjectConfigManager(MutablePydanticResourceManager[ProjectConfig]):
    """Manages the .fmu configuration file in a project."""

    fmu_dir: ProjectFMUDirectory

    def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initializes the ProjectConfig resource manager."""
        super().__init__(
            fmu_dir,
            ProjectConfig,
            migration_manager=MigrationManager(
                ProjectConfig,
                PROJECT_CONFIG_MIGRATIONS,
            ),
        )

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the config file."""
        return Path("config.json")

    @property
    def diff_ignore_fields(self: Self) -> list[str]:
        """Returns a list of all config fields that should be ignored in a diff."""
        return ["created_at", "created_by", "last_modified_at", "last_modified_by"]

    @property
    def diff_list_keys(self: Self) -> Mapping[str, str]:
        """List field identity keys used for per-item diffing."""
        return {
            "rms.zones": "name",
            "rms.horizons": "name",
            "rms.wells": "name",
            "masterdata.smda.country": "uuid",
            "masterdata.smda.discovery": "uuid",
            "masterdata.smda.field": "uuid",
            "associated_fields": "uuid",
        }

    def save(self: Self, model: ProjectConfig) -> None:
        """Save the ProjectConfig to disk, updating last_modified fields."""
        model_dict = model.model_dump()
        model_dict["last_modified_at"] = datetime.now(UTC)
        model_dict["last_modified_by"] = getpass.getuser()
        updated_model = ProjectConfig.model_validate(model_dict)
        super().save(updated_model)

    def set(self: Self, key: str, value: Any) -> None:
        """Sets a project config value by key and writes to changelog."""
        old_config = self.load()
        super().set(key, value)
        self.fmu_dir.changelog.log_update_to_changelog(
            updates={key: value},
            structured_diff=self.get_structured_model_diff(
                current_model=old_config, incoming_model=self.load()
            ),
            relative_path=self.relative_path,
        )

    def update(self: Self, updates: dict[str, Any]) -> ProjectConfig:
        """Updates project config values and writes to changelog."""
        old_config = self.load()
        updated_resource = super().update(updates)
        self.fmu_dir.changelog.log_update_to_changelog(
            updates=updates,
            structured_diff=self.get_structured_model_diff(
                current_model=old_config, incoming_model=updated_resource
            ),
            relative_path=self.relative_path,
        )
        return updated_resource

    def restore_from_cache(self: Self, revision_id: str) -> None:
        """Restore the config from a cache revision and apply its cache retention.

        Args:
            revision_id: The revision filename to restore from.

        Raises:
            FileNotFoundError: If the cache revision doesn't exist.
            MigrationError: If the cached content cannot be migrated to the current
                schema.
            ValueError: If the cached content is invalid JSON or fails model
                validation.
        """
        restored_config = self.fmu_dir.cache.get_revision_content(
            self.relative_path,
            revision_id,
            model_class=ProjectConfig,
            migration_manager=self.migration_manager,
        )
        with self.fmu_dir._set_cache_retention(restored_config.cache_max_revisions):
            super().restore_from_cache(revision_id)

    def restore_from_migration_backup(self: Self, backup: ProjectConfig) -> None:
        """Overwrite the config with a migration backup and apply its retention.

        Args:
            backup: A backup model from ``find_latest_compatible_migration_backup``.

        Raises:
            PermissionError: If another process holds the write lock.
        """
        with self.fmu_dir._set_cache_retention(backup.cache_max_revisions):
            super().restore_from_migration_backup(backup)


class UserConfigManager(MutablePydanticResourceManager[UserConfig]):
    """Manages the .fmu configuration file in a user's home directory."""

    def __init__(self: Self, fmu_dir: UserFMUDirectory) -> None:
        """Initializes the UserConfig resource manager."""
        super().__init__(
            fmu_dir,
            UserConfig,
            migration_manager=MigrationManager(
                UserConfig,
                USER_CONFIG_MIGRATIONS,
            ),
        )

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
