"""Initializes the .fmu directory."""

from pathlib import Path
from typing import Any, Final

from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._fmu_dir import ProjectFMUDirectory, UserFMUDirectory
from ._logging import null_logger
from ._readme_texts import PROJECT_README_CONTENT, USER_README_CONTENT
from ._resources.lock_manager import DEFAULT_LOCK_TIMEOUT
from .models.project_config import ProjectConfig

logger: Final = null_logger(__name__)


def _create_fmu_directory(base_path: Path) -> None:
    """Creates the .fmu directory.

    Args:
        base_path: Base directory where .fmu should be created

    Raises:
        FileNotFoundError: If base_path doesn't exist
        FileExistsError: If .fmu exists
    """
    logger.debug(f"Creating .fmu directory in '{base_path}'")

    if not base_path.exists():
        raise FileNotFoundError(
            f"Base path '{base_path}' does not exist. Expected the root "
            "directory of an FMU project."
        )

    fmu_dir = base_path / ".fmu"
    if fmu_dir.exists():
        if fmu_dir.is_dir():
            raise FileExistsError(f"{fmu_dir} already exists")
        raise FileExistsError(f"{fmu_dir} exists but is not a directory")

    fmu_dir.mkdir()
    logger.debug(f"Created .fmu directory at '{fmu_dir}'")


def init_fmu_directory(
    base_path: str | Path,
    config_data: ProjectConfig | dict[str, Any] | None = None,
    global_config: GlobalConfiguration | None = None,
    *,
    lock_timeout_seconds: int = DEFAULT_LOCK_TIMEOUT,
) -> ProjectFMUDirectory:
    """Creates and initializes a .fmu directory.

    Also initializes a configuration file if configuration data is provided through the
    function.

    Args:
        base_path: Directory where .fmu should be created.
        config_data: Optional ProjectConfig instance or dictionary with configuration
          data.
        global_config: Optional GlobaConfiguration instance with existing global config
          data.
        lock_timeout_seconds: Lock expiration time in seconds. Default 20 minutes.

    Returns:
        Instance of FMUDirectory

    Raises:
        FileExistsError: If .fmu exists
        FileNotFoundError: If base_path doesn't exist
        PermissionError: If the user lacks permission to create directories
        ValidationError: If config_data fails validationg
    """
    logger.debug("Initializing .fmu directory")
    base_path = Path(base_path)

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
        Instance of FMUDirectory

    Raises:
        FileExistsError: If .fmu exists
        FileNotFoundError: If base_path doesn't exist
        PermissionError: If the user lacks permission to create directories
        ValidationError: If config_data fails validationg
    """
    logger.debug("Initializing .fmu directory")

    _create_fmu_directory(Path.home())

    fmu_dir = UserFMUDirectory(lock_timeout_seconds=lock_timeout_seconds)
    fmu_dir.write_text_file("README", USER_README_CONTENT)

    fmu_dir.config.reset()
    logger.debug(f"Successfully initialized .fmu directory at '{fmu_dir}'")
    return fmu_dir
