"""Root configuration for pytest."""

from datetime import UTC, datetime
from typing import Any

import pytest
from pytest_lazy_fixtures import lf

from fmu.settings import __version__
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
