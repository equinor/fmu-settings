"""Module to hold the actual create function.

This function must be kept separate from the __main__ module to prevent import conflicts
if exposed from __init__.
"""

from pathlib import Path

from fmu.datamodels.context.mappings import StratigraphyMappings
from fmu.settings import ProjectFMUDirectory
from fmu.settings._init import init_fmu_directory

from ._data import PROJECT_CONFIG_DICT, STRATIGRAPHY_MAPPINGS


def create_drogon_fmu_dir(base_path: Path) -> ProjectFMUDirectory:
    """Creates a Drogon .fmu/ at base_path."""
    fmu_dir = init_fmu_directory(
        base_path,
        config_data=PROJECT_CONFIG_DICT,
        force=True,
    )

    stratigraphy_mappings = StratigraphyMappings.model_validate(STRATIGRAPHY_MAPPINGS)
    fmu_dir._mappings.update_stratigraphy_mappings(stratigraphy_mappings)

    return fmu_dir
