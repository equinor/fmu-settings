"""Root configuration for pytest."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from fmu.settings._fmu_dir import FMUDirectory
from fmu.settings._init import init_fmu_directory
from fmu.settings._version import __version__
from fmu.settings.models.config import Config


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
        "masterdata": {
            "smda": None,
        },
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
def config_dict_with_masterdata(
    unix_epoch_utc: datetime, masterdata_dict: dict[str, Any]
) -> dict[str, Any]:
    """A dictionary representing a .fmu config."""
    return {
        "version": __version__,
        "created_at": unix_epoch_utc,
        "created_by": "user",
        "masterdata": masterdata_dict,
    }


@pytest.fixture
def config_model(config_dict: dict[str, Any]) -> Config:
    """A Config model representing a .fmu config file."""
    return Config.model_validate(config_dict)


@pytest.fixture
def config_model_with_masterdata(config_dict_with_masterdata: dict[str, Any]) -> Config:
    """A Config model representing a .fmu config file."""
    return Config.model_validate(config_dict_with_masterdata)


@pytest.fixture
def fmu_dir(tmp_path: Path, unix_epoch_utc: datetime) -> FMUDirectory:
    """Create an FMUDirectory instance for testing."""
    with (
        patch("fmu.settings.resources.config.getpass.getuser", return_value="user"),
        patch("fmu.settings.resources.config.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = unix_epoch_utc
        mock_datetime.datetime.now.return_value = unix_epoch_utc

        return init_fmu_directory(tmp_path)
