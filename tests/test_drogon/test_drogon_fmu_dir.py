"""Test content of Drogon .fmu/ is correct."""

from pathlib import Path

from fmu.settings._drogon import (
    ACCESS,
    MASTERDATA,
    MODEL,
    RMS_COORDINATE_SYSTEM,
    RMS_HORIZONS,
    RMS_WELLS,
    RMS_ZONES,
    STRATIGRAPHY_MAPPINGS,
    create_drogon_fmu_dir,
)


def test_create_drogon_fmu_roundtrip(tmp_path: Path) -> None:
    """Ensure content of .fmu/ProjectFMUDirectory is as expected."""
    fmu_dir = create_drogon_fmu_dir(tmp_path)
    assert fmu_dir.path.parent == tmp_path

    config_dict = fmu_dir.config.load().model_dump(mode="json")
    assert config_dict["masterdata"] == MASTERDATA
    assert config_dict["model"] == MODEL
    assert config_dict["access"] == ACCESS

    mappings_dict = fmu_dir.mappings.load().model_dump(mode="json")

    strat_mappings = []
    for strat_mapping in mappings_dict.get("stratigraphy", []):
        assert strat_mapping.get("mapping_type") == "stratigraphy"
        assert strat_mapping.get("source_uuid") is None

        modified_mapping = {
            k: v
            for k, v in strat_mapping.items()
            if k not in ("mapping_type", "source_uuid")  # Filter these out to compare
        }
        strat_mappings.append(modified_mapping)

    assert strat_mappings == STRATIGRAPHY_MAPPINGS

    assert config_dict["rms"]["path"] == "rms/model/drogon.rms15.0.1.0"
    assert config_dict["rms"]["version"] == "15.0.1.0"
    assert config_dict["rms"]["coordinate_system"] == RMS_COORDINATE_SYSTEM
    assert config_dict["rms"]["zones"] == RMS_ZONES
    assert config_dict["rms"]["horizons"] == RMS_HORIZONS
    assert config_dict["rms"]["wells"] == RMS_WELLS
