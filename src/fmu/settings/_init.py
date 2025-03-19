"""Initializes the .fmu directory."""

from pathlib import Path
from textwrap import dedent
from typing import Any, Final

from ._fmu_dir import FMUDirectory
from ._logging import null_logger
from .resources.config import Config

logger: Final = null_logger(__name__)

_README = dedent("""\
    This directory contains static configuration data for your FMU project.

    You should *not* manually modify files within this directory. Doing so may
    result in erroneous behavior or erroneous data in your FMU project.

    Changes to data stored within this directory must happen through the FMU
    Settings application.

    Run `fmu-settings` to do this.
""")


def _create_fmu_directory(base_path: Path) -> FMUDirectory:
    """Creates the .fmu directory.

    Args:
        base_path: Base directory where .fmu should be created

    Raises:
        FileNotFoundError: If base_path doesn't exist
        FileExistsError: If .fmu exists

    Returns:
        Instance of FMUDirectory
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
    return FMUDirectory(base_path)


def init_fmu_directory(
    base_path: str | Path, config_data: Config | dict[str, Any] | None = None
) -> FMUDirectory:
    """Creates and initializes a .fmu directory.

    Also initializes a configuration file if configuration data is provided through the
    function.

    Args:
        base_path: Directory where .fmu should be created
        config_data: Optional Config instance or dictionary with configuration data

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

    fmu_dir = FMUDirectory(base_path, search_parents=False)
    fmu_dir.write_text_file("README", _README)

    fmu_dir.config.reset()
    if config_data:
        if isinstance(config_data, Config):
            config_dict = config_data.model_dump()
            fmu_dir.update_config(config_dict)
        elif isinstance(config_data, dict):
            fmu_dir.update_config(config_data)

    logger.debug(f"Successfully initialized .fmu directory at '{fmu_dir}'")
    return fmu_dir
