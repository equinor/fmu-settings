"""Functions related to finding and validating an existing global configuration."""

from pathlib import Path
from typing import Final

from pydantic import ValidationError

from fmu.config.utilities import yaml_load
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._logging import null_logger

logger: Final = null_logger(__name__)


class InvalidGlobalConfigurationError(ValueError):
    """Raised when a GlobalConfiguration contains invalid or disallowed content.

    This includes Drogon test data or other disallowed masterdata.
    This error is only raised when strict validation is enabled.
    """


# These should all be normalized to lower case.
INVALID_NAMES: Final[tuple[str, ...]] = (
    "drogon",
    "drogon_2020",
    "drogon_has_no_stratcolumn",
)
INVALID_UUIDS: Final[tuple[str, ...]] = (
    "ad214d85-dac7-19da-e053-c918a4889309",
    "ad214d85-8a1d-19da-e053-c918a4889310",
    "00000000-0000-0000-0000-000000000000",
)
INVALID_STRAT_NAMES: Final[tuple[str, ...]] = (
    "basevolantis",
    "basetherys",
    "basevalysar",
    "basevolon",
    "therys",
    "toptherys",
    "topvolantis",
    "topvolon",
    "topvalysar",
    "valysar",
    "volantis",
    "volon",
)


def validate_global_configuration_strictly(cfg: GlobalConfiguration) -> None:  # noqa: PLR0912
    """Does stricter checks against a valid GlobalConfiguration file.

    This is to prevent importing existing but incorrect data that should not make it
    into a project .fmu configuration. An example of this is Drogon masterdata.

    Args:
        cfg: A GlobalConfiguration instance to be validated

    Raises:
        InvalidGlobalConfigurationError: If some value in the GlobalConfiguration
            is invalid or not allowed
    """
    # Check model and access
    if cfg.model.name.lower() in INVALID_NAMES:
        raise InvalidGlobalConfigurationError(
            f"Invalid name in 'model': {cfg.model.name}"
        )
    if cfg.access.asset.name.lower() in INVALID_NAMES:
        raise InvalidGlobalConfigurationError(
            f"Invalid name in 'access.asset': {cfg.access.asset.name}"
        )

    # Check masterdata

    # smda.country
    for country in cfg.masterdata.smda.country:
        if str(country.uuid) in INVALID_UUIDS:
            raise InvalidGlobalConfigurationError(
                f"Invalid SMDA UUID in 'smda.country': {country.uuid}"
            )

    # smda.discovery
    for discovery in cfg.masterdata.smda.discovery:
        if discovery.short_identifier.lower() in INVALID_NAMES:
            raise InvalidGlobalConfigurationError(
                f"Invalid SMDA short identifier in 'smda.discovery': "
                f"{discovery.short_identifier}"
            )
        if str(discovery.uuid) in INVALID_UUIDS:
            raise InvalidGlobalConfigurationError(
                f"Invalid SMDA UUID in 'smda.discovery': {discovery.uuid}"
            )

    # smda.field
    for field in cfg.masterdata.smda.field:
        if field.identifier.lower() in INVALID_NAMES:
            raise InvalidGlobalConfigurationError(
                f"Invalid SMDA identifier in 'smda.field': {field.identifier}"
            )
        if str(field.uuid) in INVALID_UUIDS:
            raise InvalidGlobalConfigurationError(
                f"Invalid SMDA UUID in 'smda.field': {field.uuid}"
            )

    # smda.coordinate_system
    if (coord_uuid := str(cfg.masterdata.smda.coordinate_system.uuid)) in INVALID_UUIDS:
        raise InvalidGlobalConfigurationError(
            f"Invalid SMDA UUID in 'smda.coordinate_system': {coord_uuid}"
        )

    # smda.stratigraphic_column
    strat = cfg.masterdata.smda.stratigraphic_column
    if strat.identifier.lower() in INVALID_NAMES:
        raise InvalidGlobalConfigurationError(
            f"Invalid SMDA identifier in 'smda.stratigraphic_column': "
            f"{strat.identifier}"
        )
    if str(strat.uuid) in INVALID_UUIDS:
        raise InvalidGlobalConfigurationError(
            f"Invalid SMDA UUID in 'smda.stratigraphic_column': {strat.uuid}"
        )

    # Check stratigraphy

    if cfg.stratigraphy:
        for key in cfg.stratigraphy:
            if key.lower() in INVALID_STRAT_NAMES:
                raise InvalidGlobalConfigurationError(
                    f"Invalid stratigraphy name in 'smda.stratigraphy': {key}"
                )


def load_global_configuration_if_present(
    path: Path, fmu_load: bool = False
) -> GlobalConfiguration | None:
    """Loads a global config/global variables at a path.

    This loads via fmu-config, which is capable of loading a global _config_, which is
    different from the global _variables_ in that it may still be in separate files
    linked by the custom '!include' directive.

    Args:
        path: The path to the yaml file
        fmu_load: Whether or not to load in the custom 'fmu' format. Default False.

    Returns:
        GlobalConfiguration instance or None if file cannot be loaded.

    Raises:
        ValidationError: If the file is loaded but has invalid schema.
    """
    loader = "fmu" if fmu_load else "standard"
    try:
        global_variables_dict = yaml_load(path, loader=loader)
        global_config = GlobalConfiguration.model_validate(global_variables_dict)
        logger.debug(f"Global variables at {path} has valid settings data")
    except ValidationError:
        raise
    except Exception as e:
        logger.debug(
            f"Failed to load global variables at {path}: {type(e).__name__}: {e}"
        )
        return None
    return global_config


def _find_global_variables_file(paths: list[Path]) -> GlobalConfiguration | None:
    """Finds a valid global variables file, or not.

    This is the _output_ file after fmuconfig is run.

    Args:
        paths: A list of Paths to check.

    Returns:
        A validated GlobalConfiguration or None.

    Raises:
        ValidationError: If a file is found but has invalid schema.
    """
    for path in paths:
        if not path.exists():
            continue

        global_variables_path = path
        # If the path is a dir, and doesn't contain the right file, move on.
        if path.is_dir():
            global_variables_path = path / "global_variables.yml"
            if not global_variables_path.exists():
                continue

        logger.info(f"Found global variables at {path}")
        global_config = load_global_configuration_if_present(global_variables_path)
        if not global_config:
            continue
        return global_config

    return None


def _find_global_config_file(paths: list[Path]) -> GlobalConfiguration | None:
    """Finds a valid global configuration file, or not.

    This is the _input_ file, before fmuconfig is run.

    Args:
        paths: A list of Paths to check.

    Returns:
        A validated GlobalConfiguration or None.

    Raises:
        ValidationError: If a file is found but has invalid schema.
    """
    for path in paths:
        if not path.exists():
            continue

        logger.info(f"Found global config at {path}")
        # May be global_config*.yml or global_master*.yml
        for global_config_path in path.glob("**/global*.yml"):
            global_config = load_global_configuration_if_present(
                global_config_path, fmu_load=True
            )
            if not global_config:
                continue
            return global_config

    return None


def find_global_config(
    base_path: str | Path,
    extra_output_paths: list[Path] | None = None,
    extra_input_dirs: list[Path] | None = None,
    strict: bool = True,
) -> GlobalConfiguration | None:
    """Try to locate a global configuration with valid masterdata in known location.

    Extra paths may be provided

    Args:
        base_path: The path to the project root
        extra_output_paths: A list of extra paths to a global _variables_.
        extra_input_dirs: A list of extra dirs to a global _config_ might be.
        strict: If True, valid data but invalid _content_ is disallowed, i.e.  Drogon
            data. Default True.

    Returns:
        A valid GlobalConfiguration instance, or None.

    Raises:
        ValidationError: If a configuration file is found but has invalid schema.
        InvalidGlobalConfigurationError: If strict=True and configuration contains
            disallowed content (e.g., Drogon data).
    """
    base_path = Path(base_path)

    # Loads with 'fmu_load=False'
    known_output_paths = [base_path / "fmuconfig/output/global_variables.yml"]
    if extra_output_paths:
        known_output_paths += extra_output_paths

    global_config = _find_global_variables_file(known_output_paths)
    if global_config:
        if strict:
            validate_global_configuration_strictly(global_config)
        return global_config

    # Loads with 'fmu_load=True'
    known_input_paths = [base_path / "fmuconfig/input"]
    if extra_input_dirs:
        known_input_paths += extra_input_dirs

    global_config = _find_global_config_file(known_input_paths)
    if global_config:
        if strict:
            validate_global_configuration_strictly(global_config)
        return global_config

    logger.info("No global variables or config with valid settings data found.")
    return None
