"""Main interface for working with .fmu directory."""

from pathlib import Path
from typing import Any, Final, Self, TypeAlias, cast

from ._logging import null_logger
from ._resources.config_managers import (
    ProjectConfigManager,
    UserConfigManager,
)
from ._resources.lock_manager import LockManager
from .models.project_config import ProjectConfig
from .models.user_config import UserConfig

logger: Final = null_logger(__name__)

FMUConfigManager: TypeAlias = ProjectConfigManager | UserConfigManager


class FMUDirectoryBase:
    """Provides access to a .fmu directory and operations on its contents."""

    config: FMUConfigManager
    _lock: LockManager

    def __init__(self: Self, base_path: str | Path) -> None:
        """Initializes access to a .fmu directory.

        Args:
            base_path: The directory containing the .fmu directory or one of its parent
                dirs

        Raises:
            FileExistsError: If .fmu exists but is not a directory
            FileNotFoundError: If .fmu directory doesn't exist
            PermissionError: If lacking permissions to read/write to the directory
        """
        self.base_path = Path(base_path).resolve()
        logger.debug(f"Initializing FMUDirectory from '{base_path}'")
        self._lock = LockManager(self)

        fmu_dir = self.base_path / ".fmu"
        if fmu_dir.exists():
            if fmu_dir.is_dir():
                self._path = fmu_dir
            else:
                raise FileExistsError(
                    f".fmu exists at {self.base_path} but is not a directory"
                )
        else:
            raise FileNotFoundError(f"No .fmu directory found at {self.base_path}")

        logger.debug(f"Using .fmu directory at {self._path}")

    @property
    def path(self: Self) -> Path:
        """Returns the path to the .fmu directory."""
        return self._path

    def get_config_value(self: Self, key: str, default: Any = None) -> Any:
        """Gets a configuration value by key.

        Supports dot notation for nested values (e.g., "foo.bar")

        Args:
            key: The configuration key
            default: Value to return if key is not found. Default None

        Returns:
            The configuration value or deafult
        """
        return self.config.get(key, default)

    def set_config_value(self: Self, key: str, value: Any) -> None:
        """Sets a configuration value by key.

        Args:
            key: The configuration key
            value: The value to set

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updated config is invalid
        """
        self.config.set(key, value)

    def update_config(
        self: Self, updates: dict[str, Any]
    ) -> ProjectConfig | UserConfig:
        """Updates multiple configuration values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated *Config object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updates config is invalid
        """
        return self.config.update(updates)

    def get_file_path(self: Self, relative_path: str | Path) -> Path:
        """Gets the absolute path to a file within the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory

        Returns:
            Absolute path to the file
        """
        return self.path / relative_path

    def read_file(self, relative_path: str | Path) -> bytes:
        """Reads a file from the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        file_path = self.get_file_path(relative_path)
        return file_path.read_bytes()

    def read_text_file(self, relative_path: str | Path, encoding: str = "utf-8") -> str:
        """Reads a text file from the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory
            encoding: Text encoding to use. Default utf-8

        Returns:
            File contents as string
        """
        file_path = self.get_file_path(relative_path)
        return file_path.read_text(encoding=encoding)

    def write_file(self, relative_path: str | Path, data: bytes) -> None:
        """Writes bytes to a file in the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory
            data: Bytes to write
        """
        file_path = self.get_file_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_bytes(data)
        logger.debug(f"Wrote {len(data)} bytes to {file_path}")

    def write_text_file(
        self, relative_path: str | Path, content: str, encoding: str = "utf-8"
    ) -> None:
        """Writes text to a file in the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory
            content: Text content to write
            encoding: Text encoding to use. Default utf-8
        """
        file_path = self.get_file_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content, encoding=encoding)
        logger.debug(f"Wrote text file to {file_path}")

    def list_files(self, subdirectory: str | Path | None = None) -> list[Path]:
        """Lists files in the .fmu directory or a subdirectory.

        Args:
            subdirectory: Optional subdirectory to list files from

        Returns:
            List of Path objects for files (not directories)
        """
        base = self.get_file_path(subdirectory) if subdirectory else self.path
        if not base.exists():
            return []

        return [p for p in base.iterdir() if p.is_file()]

    def ensure_directory(self, relative_path: str | Path) -> Path:
        """Ensures a subdirectory exists in the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory

        Returns:
            Path to the directory
        """
        dir_path = self.get_file_path(relative_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def file_exists(self, relative_path: str | Path) -> bool:
        """Checks if a file exists in the .fmu directory.

        Args:
            relative_path: Path relative to the .fmu directory

        Returns:
            True if the file exists, False otherwise
        """
        return self.get_file_path(relative_path).exists()


class ProjectFMUDirectory(FMUDirectoryBase):
    config: ProjectConfigManager

    def __init__(self, base_path: str | Path) -> None:
        """Initializes a project-based .fmu directory."""
        self.config = ProjectConfigManager(self)
        super().__init__(base_path)

    def update_config(self: Self, updates: dict[str, Any]) -> ProjectConfig:
        """Updates multiple configuration values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated ProjectConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updates config is invalid
        """
        return cast("ProjectConfig", super().update_config(updates))

    @staticmethod
    def find_fmu_directory(start_path: Path) -> Path | None:
        """Searches for a .fmu directory in start_path and its parents.

        Args:
            start_path: The path to start searching from

        Returns:
            Path to the found .fmu directory or None if not found
        """
        current = start_path
        # Prevent symlink loops
        visited = set()

        while current not in visited:
            visited.add(current)
            fmu_dir = current / ".fmu"

            # Do not include $HOME/.fmu in the search
            if fmu_dir.is_dir() and current != Path.home():
                return fmu_dir

            # We hit root
            if current == current.parent:
                break

            current = current.parent

        return None

    @classmethod
    def find_nearest(cls: type[Self], start_path: str | Path = ".") -> Self:
        """Factory method to find and open the nearest .fmu directory.

        Args:
            start_path: Path to start searching from. Default current working director

        Returns:
            FMUDirectory instance

        Raises:
            FileNotFoundError: If no .fmu directory is found
        """
        start_path = Path(start_path).resolve()
        fmu_dir_path = cls.find_fmu_directory(start_path)
        if fmu_dir_path is None:
            raise FileNotFoundError(f"No .fmu directory found at or above {start_path}")
        return cls(fmu_dir_path.parent)


class UserFMUDirectory(FMUDirectoryBase):
    config: UserConfigManager

    def __init__(self) -> None:
        """Initializes a project-based .fmu directory."""
        self.config = UserConfigManager(self)
        super().__init__(Path.home())

    def update_config(self: Self, updates: dict[str, Any]) -> UserConfig:
        """Updates multiple configuration values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated UserConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If the updates config is invalid
        """
        return cast("UserConfig", super().update_config(updates))


def get_fmu_directory(base_path: str | Path) -> ProjectFMUDirectory:
    """Initializes access to a .fmu directory.

    Args:
        base_path: The directory containing the .fmu directory or one of its parent
                   dirs

    Returns:
        FMUDirectory instance

    Raises:
        FileExistsError: If .fmu exists but is not a directory
        FileNotFoundError: If .fmu directory doesn't exist
        PermissionError: If lacking permissions to read/write to the directory

    """
    return ProjectFMUDirectory(base_path)


def find_nearest_fmu_directory(start_path: str | Path = ".") -> ProjectFMUDirectory:
    """Factory method to find and open the nearest .fmu directory.

    Args:
        start_path: Path to start searching from. Default current working directory

    Returns:
        FMUDirectory instance

    Raises:
        FileNotFoundError: If no .fmu directory is found
    """
    return ProjectFMUDirectory.find_nearest(start_path)
