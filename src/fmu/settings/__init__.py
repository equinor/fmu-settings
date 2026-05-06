"""The fmu-settings package."""

try:
    from ._version import version

    __version__: str = version
except ImportError:
    __version__ = version = "0.0.0"

from ._fmu_dir import (
    ProjectFMUDirectory,
    UserFMUDirectory,
    find_nearest_fmu_directory,
    get_fmu_directory,
)
from ._init import (
    REQUIRED_FMU_PROJECT_SUBDIRS,
    InvalidFMUProjectPathError,
    init_fmu_directory,
    init_user_fmu_directory,
)
from .models._enums import CacheResource
from .models.mappings import (
    InternalBaseMapping,
    InternalIdentifierMapping,
    InternalMappings,
    InternalRelationType,
    InternalStratigraphyIdentifierMapping,
    InternalStratigraphyMappings,
    InternalWellboreIdentifierMapping,
    InternalWellboreMappings,
)

__all__ = [
    "CacheResource",
    "get_fmu_directory",
    "init_fmu_directory",
    "init_user_fmu_directory",
    "InternalBaseMapping",
    "InternalIdentifierMapping",
    "InternalMappings",
    "InternalRelationType",
    "InternalStratigraphyIdentifierMapping",
    "InternalStratigraphyMappings",
    "InternalWellboreIdentifierMapping",
    "InternalWellboreMappings",
    "InvalidFMUProjectPathError",
    "ProjectFMUDirectory",
    "REQUIRED_FMU_PROJECT_SUBDIRS",
    "UserFMUDirectory",
    "find_nearest_fmu_directory",
]
