"""Root configuration for pytest."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
import yaml
from fmu.datamodels.fmu_results import fields
from fmu.datamodels.fmu_results.enums import Classification
from fmu.datamodels.fmu_results.global_configuration import (
    Access,
    GlobalConfiguration,
    Stratigraphy,
    StratigraphyElement,
)
from pytest import MonkeyPatch

from fmu.settings._fmu_dir import ProjectFMUDirectory, UserFMUDirectory
from fmu.settings._init import init_fmu_directory, init_user_fmu_directory
from fmu.settings._version import __version__
from fmu.settings.models.project_config import ProjectConfig
from fmu.settings.models.user_config import UserConfig


@pytest.fixture
def unix_epoch_utc() -> datetime:
    """Returns a fixed datetime used in testing."""
    return datetime(1970, 1, 1, 0, 0, tzinfo=UTC)


@pytest.fixture
def config_dict(unix_epoch_utc: datetime) -> dict[str, Any]:
    """A dictionary representing a .fmu config."""
    return {
        "version": __version__,
        "created_at": unix_epoch_utc,
        "created_by": "user",
        "cache_max_revisions": 5,
        "masterdata": None,
        "model": None,
        "access": None,
    }


@pytest.fixture
def masterdata_dict() -> dict[str, Any]:
    """Example masterdata from SMDA."""
    return {
        "smda": {
            "country": [
                {
                    "identifier": "Norway",
                    "uuid": "ad214d85-8a1d-19da-e053-c918a4889309",
                }
            ],
            "discovery": [
                {
                    "short_identifier": "DROGON",
                    "uuid": "ad214d85-8a1d-19da-e053-c918a4889309",
                }
            ],
            "field": [
                {
                    "identifier": "DROGON",
                    "uuid": "ad214d85-8a1d-19da-e053-c918a4889309",
                }
            ],
            "coordinate_system": {
                "identifier": "ST_WGS84_UTM37N_P32637",
                "uuid": "ad214d85-dac7-19da-e053-c918a4889309",
            },
            "stratigraphic_column": {
                "identifier": "DROGON_HAS_NO_STRATCOLUMN",
                "uuid": "ad214d85-8a1d-19da-e053-c918a4889309",
            },
        }
    }


@pytest.fixture
def model_dict() -> dict[str, Any]:
    """Example model information."""
    return {
        "name": "Drogon",
        "revision": "21.0.0",
        "description": None,
    }


@pytest.fixture
def access_dict() -> dict[str, Any]:
    """Example access information."""
    return {
        "asset": {"name": "Drogon"},
        "classification": "internal",
    }


@pytest.fixture
def stratigraphy_dict() -> dict[str, Any]:
    """Example stratigraphy information."""
    return {
        "MSL": {
            "stratigraphic": False,
            "name": "MSL",
        },
        "Seabase": {
            "stratigraphic": False,
            "name": "Seabase",
        },
        "TopVolantis": {
            "stratigraphic": True,
            "name": "VOLANTIS GP. Top",
            "alias": ["TopVOLANTIS", "TOP_VOLANTIS"],
            "stratigraphic_alias": ["TopValysar", "Valysar Fm. Top"],
        },
        "TopTherys": {"stratigraphic": True, "name": "Therys Fm. Top"},
        "TopVolon": {"stratigraphic": True, "name": "Volon Fm. Top"},
        "BaseVolon": {"stratigraphic": True, "name": "Volon Fm. Base"},
        "BaseVolantis": {"stratigraphic": True, "name": "VOLANTIS GP. Base"},
        "Mantle": {"stratigraphic": False, "name": "Mantle"},
        "Above": {"stratigraphic": False, "name": "Above"},
        "Valysar": {"stratigraphic": True, "name": "Valysar Fm."},
        "Therys": {"stratigraphic": True, "name": "Therys Fm."},
        "Volon": {"stratigraphic": True, "name": "Volon Fm."},
        "Below": {"stratigraphic": False, "name": "Below"},
    }


@pytest.fixture
def global_variables_without_masterdata() -> dict[str, Any]:
    """Example global_variables.yml file without masterdata."""
    return {
        "global": {
            "dates": ["2018-01-01", "2018-07-01", "2019-07-01", "2020-07-01"],
        },
    }


@pytest.fixture
def global_variables_with_masterdata(
    masterdata_dict: dict[str, Any],
    access_dict: dict[str, Any],
    model_dict: dict[str, Any],
    stratigraphy_dict: dict[str, Any],
    global_variables_without_masterdata: dict[str, Any],
) -> dict[str, Any]:
    """Example global_variables.yml file with masterdata."""
    return {
        "masterdata": masterdata_dict,
        "access": access_dict,
        "model": model_dict,
        "stratigraphy": stratigraphy_dict,
        **global_variables_without_masterdata,
    }


@pytest.fixture
def fmuconfig_with_input(  # noqa: PLR0913 too many args
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    masterdata_dict: dict[str, Any],
    access_dict: dict[str, Any],
    model_dict: dict[str, Any],
    stratigraphy_dict: dict[str, Any],
    global_variables_without_masterdata: dict[str, Any],
) -> Path:
    """Creates an fmuconfig/ path and input directory.

    Returns:
        tmp_path.
    """
    fmuconfig_input = tmp_path / "fmuconfig/input"
    fmuconfig_input.mkdir(parents=True, exist_ok=True)

    with open(fmuconfig_input / "_masterdata.yml", "w") as f:
        yaml.safe_dump(masterdata_dict, f)
    with open(fmuconfig_input / "_access.yml", "w") as f:
        yaml.safe_dump(access_dict, f)
    with open(fmuconfig_input / "_stratigraphy.yml", "w") as f:
        yaml.safe_dump(stratigraphy_dict, f)

    global_config_dict = {
        **global_variables_without_masterdata,
        "model": model_dict,
        "masterdata": "!include _masterdata.yml",
        "access": "!include _access.yml",
        "stratigraphy": "!include _stratigraphy.yml",
    }
    # Remove quotes around strings. PyYAML quotes string beginning with ! by default as
    # they indicate a yaml tag, for which fmu-config has defined one in this case.
    global_config_yml = yaml.dump(
        global_config_dict, default_style=None, default_flow_style=False
    ).replace("'", "")

    with open(fmuconfig_input / "global_master_config.yml", "w") as f:
        f.write(global_config_yml)

    return tmp_path


@pytest.fixture
def fmuconfig_with_output(  # noqa: PLR0913 too many args
    fmuconfig_with_input: Path,
    global_variables_with_masterdata: dict[str, Any],
) -> Path:
    """Creates an fmuconfig/ path and input/output directory.

    Returns:
        tmp_path
    """
    fmuconfig_output = fmuconfig_with_input / "fmuconfig/output"
    fmuconfig_output.mkdir(parents=True, exist_ok=True)

    with open(fmuconfig_output / "global_variables.yml", "w") as f:
        yaml.safe_dump(
            global_variables_with_masterdata,
            f,
            default_style=None,
            default_flow_style=False,
        )

    return fmuconfig_with_input


@pytest.fixture
def generate_strict_valid_globalconfiguration() -> Callable[[], GlobalConfiguration]:
    """Generates a global configuration that is valid, but can switch particular models.

    All values are left empty by default.
    """

    def _generate_cfg(  # noqa: PLR0913
        *,
        classification: Classification | None = Classification.internal,
        asset: fields.Asset | None = None,
        coordinate_system: fields.CoordinateSystem | None = None,
        stratigraphic_column: fields.StratigraphicColumn | None = None,
        country_items: list[fields.CountryItem] | None = None,
        discovery_items: list[fields.DiscoveryItem] | None = None,
        field_items: list[fields.FieldItem] | None = None,
        model: fields.Model | None = None,
    ) -> GlobalConfiguration:
        return GlobalConfiguration(
            access=Access(
                asset=asset or fields.Asset(name=""), classification=classification
            ),
            masterdata=fields.Masterdata(
                smda=fields.Smda(
                    coordinate_system=(
                        coordinate_system
                        or fields.CoordinateSystem(identifier="", uuid=uuid4())
                    ),
                    stratigraphic_column=(
                        stratigraphic_column
                        or fields.StratigraphicColumn(identifier="", uuid=uuid4())
                    ),
                    country=country_items or [],
                    discovery=discovery_items or [],
                    field=field_items or [],
                )
            ),
            model=model or fields.Model(name="", revision=""),
            stratigraphy=Stratigraphy(
                {"MSL": StratigraphyElement(name="MSL", stratigraphic=False)}
            ),
        )

    return _generate_cfg


@pytest.fixture
def config_dict_with_masterdata(
    unix_epoch_utc: datetime,
    masterdata_dict: dict[str, Any],
    model_dict: dict[str, Any],
) -> dict[str, Any]:
    """A dictionary representing a .fmu config."""
    return {
        "version": __version__,
        "created_at": unix_epoch_utc,
        "created_by": "user",
        "cache_max_revisions": 5,
        "masterdata": masterdata_dict,
        "model": model_dict,
    }


@pytest.fixture
def config_model(config_dict: dict[str, Any]) -> ProjectConfig:
    """A ProjectConfig model representing a .fmu config file."""
    return ProjectConfig.model_validate(config_dict)


@pytest.fixture
def config_model_with_masterdata(
    config_dict_with_masterdata: dict[str, Any],
) -> ProjectConfig:
    """A ProjectConfig model representing a .fmu config file."""
    return ProjectConfig.model_validate(config_dict_with_masterdata)


@pytest.fixture
def user_config_dict(unix_epoch_utc: datetime) -> dict[str, Any]:
    """A dictionary representing a .fmu user config."""
    return {
        "version": __version__,
        "created_at": unix_epoch_utc,
        "cache_max_revisions": 5,
        "user_api_keys": {
            "smda_subscription": None,
        },
        "recent_project_directories": [],
    }


@pytest.fixture
def user_config_model(user_config_dict: dict[str, Any]) -> UserConfig:
    """A UserConfig model representing a .fmu config file."""
    return UserConfig.model_validate(user_config_dict)


@pytest.fixture(scope="function")
def fmu_dir(tmp_path: Path, unix_epoch_utc: datetime) -> ProjectFMUDirectory:
    """Create an ProjectFMUDirectory instance for testing."""
    with (
        patch(
            "fmu.settings.models.project_config.getpass.getuser",
            return_value="user",
        ),
        patch("fmu.settings.models.project_config.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = unix_epoch_utc
        mock_datetime.datetime.now.return_value = unix_epoch_utc
        return init_fmu_directory(tmp_path)


@pytest.fixture
def user_fmu_dir(tmp_path: Path, unix_epoch_utc: datetime) -> UserFMUDirectory:
    """Create an ProjectFMUDirectory instance for testing."""
    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch("fmu.settings.models.user_config.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = unix_epoch_utc
        mock_datetime.datetime.now.return_value = unix_epoch_utc

        return init_user_fmu_directory()
