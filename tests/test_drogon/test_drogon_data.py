"""Checks that all Drogon .fmu/ data validates against current fmu-datamodels."""

from typing import Any

from fmu.datamodels import Access, Masterdata
from fmu.datamodels.context.mappings import StratigraphyMappings
from fmu.datamodels.fmu_results.fields import Model
from fmu.datamodels.fmu_results.global_configuration import Stratigraphy

from fmu.settings.models.project_config import (
    RmsCoordinateSystem,
    RmsHorizon,
    RmsStratigraphicZone,
    RmsWell,
)


def test_masterdata_dict_validates(masterdata_dict: dict[str, Any]) -> None:
    """Drogon masterdata validates with the Masterdata model."""
    Masterdata.model_validate(masterdata_dict, extra="forbid")


def test_model_dict_validates(model_dict: dict[str, Any]) -> None:
    """Drogon model validates with the Model model."""
    Model.model_validate(model_dict, extra="forbid")


def test_access_dict_validates(access_dict: dict[str, Any]) -> None:
    """Drogon access validates with the Access model."""
    Access.model_validate(access_dict, extra="forbid")


def test_global_config_stratigraphy_validates(
    stratigraphy_dict: dict[str, Any],
) -> None:
    """Drogon global config stratigraphy validates with the Stratigraphy model."""
    Stratigraphy.model_validate(stratigraphy_dict, extra="forbid")


def test_stratigraphy_mapping_validates(
    stratigraphy_mappings_list: list[dict[str, Any]],
) -> None:
    """Drogon stratigraphy mapping validates with the StratigraphyMapping model."""
    StratigraphyMappings.model_validate(stratigraphy_mappings_list, extra="forbid")


def test_rms_zones_validates(rms_zones_list: list[dict[str, Any]]) -> None:
    """Drogon RMS zones list validates with RmsStratigraphicZone."""
    for zone in rms_zones_list:
        RmsStratigraphicZone.model_validate(zone, extra="forbid")


def test_rms_horizons_validates(rms_horizones_list: list[dict[str, Any]]) -> None:
    """Drogon RMS horizons list validates with RmsHorizon."""
    for horizon in rms_horizones_list:
        RmsHorizon.model_validate(horizon, extra="forbid")


def test_rms_wells_validates(rms_wells_list: list[dict[str, Any]]) -> None:
    """Drogon RMS wells list validates with RmsWell."""
    for well in rms_wells_list:
        RmsWell.model_validate(well, extra="forbid")


def test_rms_coordinate_system_validates(rms_coordinate_system: dict[str, str]) -> None:
    """Drogon RMS coordinate system validates with RmsCoordinateSystem."""
    RmsCoordinateSystem.model_validate(rms_coordinate_system, extra="forbid")
