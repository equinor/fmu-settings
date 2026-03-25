"""Produces a validated Drogon .fmu/ directory.

This directory is used both for testing, and for Drogon to more easily update its .fmu/
directory with changes and new releases.

Execute this with:

    python -m fmu.settings._drogon

Or, to create it at a specific path, use:

    python -m fmu.settings._drogon /some/path  # Creates /some/path/.fmu/

"""

import argparse
import sys
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


def main(args: list[str] | None = None) -> None:
    """Generate Drogon .fmu/ data."""
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Generate a Drogon .fmu/ directory.")
    parser.add_argument(
        "base_path",
        type=Path,
        nargs="?",
        help=(
            "The path to where a Drogon .fmu/ directory should be generated. If /foo "
            "is provided, will create /foo/.fmu/. Default: current working directory."
        ),
        default=Path.cwd(),
    )
    parsed_args = parser.parse_args(args)

    fmu_dir = create_drogon_fmu_dir(parsed_args.base_path)
    print(f"Created Drogon .fmu/ directory in {fmu_dir.path.parent}")


if __name__ == "__main__":
    main()
