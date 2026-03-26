"""Initializes the .fmu directory."""

from pathlib import Path
from typing import Any, Final

from pydantic import ValidationError

from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._fmu_dir import ProjectFMUDirectory, UserFMUDirectory
from ._global_config import InvalidGlobalConfigurationError, find_global_config
from ._logging import null_logger
from ._readme_texts import PROJECT_README_CONTENT, USER_README_CONTENT
from ._resources.lock_manager import DEFAULT_LOCK_TIMEOUT
from ._utils import path_exists, path_is_dir
from .models.project_config import ProjectConfig

logger: Final = null_logger(__name__)
REQUIRED_FMU_PROJECT_SUBDIRS: Final[tuple[str, ...]] = ("ert",)


class InvalidFMUProjectPathError(ValueError):
    """Raised when init is attempted outside an FMU project root."""


def is_fmu_project(path: Path) -> tuple[bool, list[str]]:
    """Ensures the provided directory looks like an FMU project.

    Args:
        path: The directory to check

    Returns:
        Tuple of bool and list of strings, indicating whether the provided path does or
        does not appear to be a valid FMU project, and what directories are lacking for
        it to be so, respectively.
    """
    missing: list[str] = []
    for dir_name in REQUIRED_FMU_PROJECT_SUBDIRS:
        required_dir = path / dir_name
        if not path_exists(required_dir) or not path_is_dir(required_dir):
            missing.append(dir_name)

    return len(missing) == 0, missing


def _create_fmu_directory(base_path: Path) -> None:
    """Creates the .fmu directory.

    Args:
        base_path: Base directory where .fmu should be created

    Raises:
        FileNotFoundError: If base_path doesn't exist
        FileExistsError: If .fmu exists
    """
    logger.debug(f"Creating .fmu directory in '{base_path}'")

    if not path_exists(base_path):
        raise FileNotFoundError(
            f"Base path '{base_path}' does not exist. Expected the root "
            "directory of an FMU project."
        )

    fmu_dir = base_path / ".fmu"
    if path_exists(fmu_dir):
        if path_is_dir(fmu_dir):
            raise FileExistsError(f"{fmu_dir} already exists")
        raise FileExistsError(f"{fmu_dir} exists but is not a directory")

    fmu_dir.mkdir()
    logger.debug(f"Created .fmu directory at '{fmu_dir}'")


def init_fmu_directory(
    base_path: str | Path,
    config_data: ProjectConfig | dict[str, Any] | None = None,
    global_config: GlobalConfiguration | None = None,
    *,
    force: bool = False,
    lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
) -> ProjectFMUDirectory:
    """Creates and initializes a .fmu directory.

    Also initializes a configuration file if configuration data is provided through the
    function.

    Args:
        base_path: Directory where .fmu should be created.
        config_data: Optional ProjectConfig instance or dictionary with configuration
          data.
        global_config: Optional GlobalConfiguration instance with existing global config
          data.
        force: Skip FMU project root validation checks.
        lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.

    Returns:
        Instance of ProjectFMUDirectory

    Raises:
        InvalidFMUProjectPathError: If base_path does not look like an FMU project
            root and force is False.
        FileExistsError: If .fmu exists
        FileNotFoundError: If base_path doesn't exist
        PermissionError: If the user lacks permission to create directories
        ValidationError: If config_data fails validation
    """
    logger.debug("Initializing .fmu directory")
    base_path = Path(base_path)

    if not force and path_exists(base_path):
        has_required_dirs, missing_dirs = is_fmu_project(base_path)
        if not has_required_dirs:
            required_dirs = ", ".join(
                f"'{dir_name}'" for dir_name in REQUIRED_FMU_PROJECT_SUBDIRS
            )
            missing_dirs_text = ", ".join(f"'{dir_name}'" for dir_name in missing_dirs)
            raise InvalidFMUProjectPathError(
                "Failed initializing .fmu directory. Initialize it from a project "
                f"root containing {required_dirs}. Did not find: "
                f"{missing_dirs_text}."
            )

    if global_config is None:
        try:
            global_config = find_global_config(base_path)
        except (InvalidGlobalConfigurationError, ValidationError) as error:
            logger.warning(
                f"Unable to auto-import global configuration from '{base_path}': "
                f"{type(error).__name__}: {error}"
            )

    _create_fmu_directory(base_path)

    fmu_dir = ProjectFMUDirectory(
        base_path,
        lock_timeout_seconds=lock_timeout_seconds,
    )
    fmu_dir.write_text_file("README", PROJECT_README_CONTENT)

    fmu_dir.config.reset()
    if config_data:
        if isinstance(config_data, ProjectConfig):
            config_data = config_data.model_dump()
        fmu_dir.update_config(config_data)

    if global_config:
        for key, value in global_config.model_dump().items():
            fmu_dir.set_config_value(key, value)

    logger.info(f"Successfully initialized .fmu directory at '{fmu_dir}'")
    return fmu_dir


def init_user_fmu_directory(
    *,
    lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
) -> UserFMUDirectory:
    """Creates and initializes a user's $HOME/.fmu directory.

    Args:
        lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.

    Returns:
        Instance of UserFMUDirectory

    Raises:
        FileExistsError: If .fmu exists
        FileNotFoundError: If base_path doesn't exist
        PermissionError: If the user lacks permission to create directories
        ValidationError: If config_data fails validation
    """
    logger.debug("Initializing .fmu directory")

    _create_fmu_directory(Path.home())

    fmu_dir = UserFMUDirectory(lock_timeout_seconds=lock_timeout_seconds)
    fmu_dir.write_text_file("README", USER_README_CONTENT)

    fmu_dir.config.reset()
    logger.debug(f"Successfully initialized .fmu directory at '{fmu_dir}'")
    return fmu_dir
