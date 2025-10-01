"""The fmu-settings package."""

try:
    from ._version import version

    __version__: str = version
except ImportError:
    __version__ = version = "0.0.0"

from ._fmu_dir import ProjectFMUDirectory, find_nearest_fmu_directory, get_fmu_directory

__all__ = ["get_fmu_directory", "ProjectFMUDirectory", "find_nearest_fmu_directory"]
