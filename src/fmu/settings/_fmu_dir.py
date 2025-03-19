"""Main interface for working with .fmu directory."""

from pathlib import Path
from typing import Any, Final, Self, cast

from ._logging import null_logger
from .resources.config import Config, ConfigManager

logger: Final = null_logger(__name__)


class FMUDirectory:
    """Provides access to a .fmu directory and operations on its contents."""

    def __init__(
        self: Self,
        base_path: str | Path,
        search_parents: bool = True,
    ) -> None:
        """Initializes access to a .fmu directory.

        Args:
            base_path: The directory containing the .fmu directory or one of its parent
                       dirs
            search_parents: If True, searches parent directories for .fmu if not found

        Raises:
            FileNotFoundError: If .fmu directory doesn't exist
            PermissionError: If lacking permissions to read/write to the directory
        """
        self.base_path = Path(base_path).resolve()

        self._path: Path | None = None
        if search_parents:
            self._path = self.find_fmu_directory(self.base_path)
        else:
            fmu_dir = self.base_path / ".fmu"
            if fmu_dir.is_dir():
                self._path = fmu_dir

        if self._path is None:
            if search_parents:
                raise FileNotFoundError(
                    f"No .fmu directory found at or above {self.base_path}"
                )
            raise FileNotFoundError(f"No .fmu directory found at {self.base_path}")

        self.config = ConfigManager(self)

        logger.debug(f"Using .fmu directory at {self._path}")

    @property
    def path(self: Self) -> Path:
        """Returns the path to the .fmu directory."""
        return cast("Path", self._path)

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

            if fmu_dir.is_dir():
                return fmu_dir

            # We hit root
            if current == current.parent:
                break

            current = current.parent

        return None

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

    def update_config(self: Self, updates: dict[str, Any]) -> Config:
        """Updates multiple configuration values at once.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            The updated Config object

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

    @classmethod
    def find_nearest(
        cls: type["FMUDirectory"], start_path: str | Path = "."
    ) -> "FMUDirectory":
        """Factory method to find and open the nearest .fmu directory.

        Args:
            start_path: Path to start searching from. Default current working director

        Returns:
            FMUDirectory instance

        Raises:
            FileNotFoundError: If no .fmu directory is found
        """
        return cls(start_path, search_parents=True)


def get_fmu_directory(base_path: Path, search_parents: bool = True) -> FMUDirectory:
    """Initializes access to a .fmu directory.

    Args:
        base_path: The directory containing the .fmu directory or one of its parent
                   dirs
        search_parents: If True, searches parent directories for .fmu if not found

    Returns:
        FMUDirectory instance

    Raises:
        FileNotFoundError: If .fmu directory doesn't exist
        PermissionError: If lacking permissions to read/write to the directory

    """
    return FMUDirectory(base_path, search_parents=search_parents)


def find_nearest_fmu_directory(start_path: str | Path = ".") -> FMUDirectory:
    """Factory method to find and open the nearest .fmu directory.

    Args:
        start_path: Path to start searching from. Default current working directory

    Returns:
        FMUDirectory instance

    Raises:
        FileNotFoundError: If no .fmu directory is found
    """
    return FMUDirectory.find_nearest(start_path)
