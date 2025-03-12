"""Initializes the .fmu directory."""

import getpass
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from fmu.settings import __version__

from ._logging import null_logger
from .models.config import Config

logger: Final = null_logger(__name__)


def _create_fmu_config(
    config_data: Config | dict[str, Any] | None,
) -> Config:
    """Creates the initial configuration file saved in .fmu.

    Args:
        config_data: A Config instance or dictionary to create one from (optional)

    Raises:
        ValidationError: If Pydantic fails to validate the config data

    Returns:
        A validated Config instance
    """
    logger.debug("Creating Config model")
    created_at = datetime.now(UTC)
    user = getpass.getuser()
    if config_data is None:
        logger.debug("Using default configuration")
        return Config(
            version=__version__,
            created_at=created_at,
            created_by=user,
        )
    if isinstance(config_data, Config):
        logger.debug("Using provided Config instance")
        config = config_data
    else:
        logger.debug("Validating provided config dictionary")
        config = Config.model_validate(config_data)

    if config.created_by != user:
        logger.warn(
            f"Config created_by is '{config.created_by}' but current user is '{user}'"
        )

    # Ensure not stale
    config.created_at = created_at

    return config


def _create_fmu_directory(base_path: Path) -> Path:
    """Creates the .fmu directory.

    Args:
        base_path: Base directory where .fmu should be created

    Raises:
        FileNotFoundError: If base_path doesn't exist
        FileExistsError: If .fmu exists

    Returns:
        Path to the .fmu directory
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
    return fmu_dir


def _write_fmu_config(fmu_dir: Path, config: Config) -> Path:
    """Writes the configuration file to .fmu/config.json.

    Args:
        fmu_dir: Path to the .fmu directory
        config: Config model instance being saved

    Returns:
        Path to the written config file
    """
    config_file = fmu_dir / "config.json"
    logger.debug(f"Writing config to '{config_file}'")

    config_json = config.model_dump(
        mode="json",
        exclude_none=True,
        by_alias=True,
    )

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_json, f, indent=2)

    logger.debug(f"Successfully wrote config to '{config_file}'")
    return config_file


def init_fmu_directory(
    base_path: str | Path, config_data: Config | dict[str, Any] | None = None
) -> Path:
    """Creates and initializes a .fmu directory.

    Also initializes a configuration file if configuration data is provided through the
    function.

    Args:
        base_path: Directory where .fmu should be created
        config_data: Optional Config instance of dictionary with configuration data

    Returns:
        Path to the .fmu directory

    Raises:
        FileExistsError: If .fmu exists
        FileNotFoundError: If base_path doesn't exist
        PermissionError: If the user lacks permission to create directories
        ValidationError: If config_data fails validationg
    """
    logger.debug("Initializing .fmu directory")
    base_path = Path(base_path)

    fmu_dir = _create_fmu_directory(base_path)
    config = _create_fmu_config(config_data)
    _write_fmu_config(fmu_dir, config)

    logger.debug(f"Successfully initialized .fmu directory at '{fmu_dir}'")
    return fmu_dir
