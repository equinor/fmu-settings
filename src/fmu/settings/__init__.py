"""The fmu-settings package."""

try:
    from ._version import version

    __version__ = version
except ImportError:
    __version__ = version = "0.0.0"

from ._fmu_dir import FMUDirectory, find_nearest_fmu_directory, get_fmu_directory

__all__ = ["get_fmu_directory", "FMUDirectory", "find_nearest_fmu_directory"]
