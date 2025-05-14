"""Initializes the .fmu directory."""

from pathlib import Path
from textwrap import dedent
from typing import Any, Final

from ._fmu_dir import ProjectFMUDirectory, UserFMUDirectory
from ._logging import null_logger
from .models.project_config import ProjectConfig

logger: Final = null_logger(__name__)

_README = dedent("""\
    This directory contains static configuration data for your FMU project.

    You should *not* manually modify files within this directory. Doing so may
    result in erroneous behavior or erroneous data in your FMU project.

    Changes to data stored within this directory must happen through the FMU
    Settings application.

    Run `fmu-settings` to do this.
""")

_USER_README = dedent("""\
    This directory contains static data and configuration elements used by some
    components in FMU. It may also contains sensitive access tokens that should not be
    shared with others.

    You should *not* manually modify files within this directory. Doing so may
    result in erroneous behavior by some FMU components.

    Changes to data stored within this directory must happen through the FMU
    Settings application.

    Run `fmu-settings` to do this.
""")


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
    base_path: str | Path, config_data: ProjectConfig | dict[str, Any] | None = None
) -> ProjectFMUDirectory:
    """Creates and initializes a .fmu directory.

    Also initializes a configuration file if configuration data is provided through the
    function.

    Args:
        base_path: Directory where .fmu should be created
        config_data: Optional ProjectConfig instance or dictionary with configuration
          data

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

    fmu_dir = ProjectFMUDirectory(base_path)
    fmu_dir.write_text_file("README", _README)

    fmu_dir.config.reset()
    if config_data:
        if isinstance(config_data, ProjectConfig):
            config_dict = config_data.model_dump()
            fmu_dir.update_config(config_dict)
        elif isinstance(config_data, dict):
            fmu_dir.update_config(config_data)

    logger.debug(f"Successfully initialized .fmu directory at '{fmu_dir}'")
    return fmu_dir


def init_user_fmu_directory() -> UserFMUDirectory:
    """Creates and initializes a user's $HOME/.fmu directory.

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

    fmu_dir = UserFMUDirectory()
    fmu_dir.write_text_file("README", _USER_README)

    fmu_dir.config.reset()
    logger.debug(f"Successfully initialized .fmu directory at '{fmu_dir}'")
    return fmu_dir
