"""Root configuration for pytest."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pytest_lazy_fixtures import lf

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
    }


@pytest.fixture
def config_model(config_dict: dict[str, Any]) -> Config:
    """A Config model representing a .fmu config file."""
    return Config.model_validate(config_dict)


@pytest.fixture(params=[None, lf("config_dict"), lf("config_model")])
def config_data_options(request: pytest.FixtureRequest) -> pytest.FixtureRequest:
    """Possible configuration inputs used when generating a new .fmu directory."""
    return request.param


@pytest.fixture
def fmu_dir_path(tmp_path: Path, config_model: Config) -> Path:
    """Create a temporary FMU directory for testing."""
    fmu_dir = init_fmu_directory(tmp_path, config_model)
    return fmu_dir.path


@pytest.fixture
def fmu_dir(fmu_dir_path: Path) -> FMUDirectory:
    """Create an FMUDirectory instance for testing."""
    return FMUDirectory(fmu_dir_path.parent, search_parents=False)
