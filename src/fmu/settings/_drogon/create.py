"""Module to hold the actual create function.

This function must be kept separate from the __main__ module to prevent import conflicts
if exposed from __init__.
"""

from pathlib import Path
from typing import Any

from fmu.datamodels.context.mappings import DataSystem, MappingType
from fmu.settings import ProjectFMUDirectory
from fmu.settings._init import init_fmu_directory
from fmu.settings.models.mappings import (
    InternalRelationType,
    InternalStratigraphyIdentifierMapping,
    InternalStratigraphyMappings,
)

from ._data import PROJECT_CONFIG_DICT, STRATIGRAPHY_MAPPINGS


def create_drogon_fmu_dir(base_path: Path) -> ProjectFMUDirectory:
    """Creates a Drogon .fmu/ at base_path."""
    fmu_dir = init_fmu_directory(
        base_path,
        config_data=PROJECT_CONFIG_DICT,
        force=True,
    )

    stratigraphy_mappings = _build_internal_stratigraphy_mappings(STRATIGRAPHY_MAPPINGS)
    fmu_dir._mappings.update_internal_stratigraphy_mappings(stratigraphy_mappings)

    return fmu_dir


def _build_internal_stratigraphy_mappings(
    mappings: list[dict[str, Any]],
) -> InternalStratigraphyMappings:
    """Build internal .fmu stratigraphy mappings from Drogon's STRATIGRAPHY_MAPPINGS."""
    primary_source_by_target: dict[str, str] = {}
    internal_mappings: list[InternalStratigraphyIdentifierMapping] = []

    for mapping in mappings:
        if mapping["relation_type"] != "primary":
            continue
        primary_source_by_target[mapping["target_id"]] = mapping["source_id"]
        internal_mappings.append(
            InternalStratigraphyIdentifierMapping(
                source_system=DataSystem(mapping["source_system"]),
                target_system=DataSystem(mapping["source_system"]),
                mapping_type=MappingType.stratigraphy,
                relation_type=InternalRelationType.primary,
                source_id=mapping["source_id"],
                source_uuid=mapping.get("source_uuid"),
                target_id=mapping["source_id"],
                target_uuid=mapping.get("source_uuid"),
            )
        )
        internal_mappings.append(
            InternalStratigraphyIdentifierMapping(
                source_system=DataSystem(mapping["source_system"]),
                target_system=DataSystem(mapping["target_system"]),
                mapping_type=MappingType.stratigraphy,
                relation_type=InternalRelationType.primary,
                source_id=mapping["source_id"],
                source_uuid=mapping.get("source_uuid"),
                target_id=mapping["target_id"],
                target_uuid=mapping.get("target_uuid"),
            )
        )

    for mapping in mappings:
        if mapping["relation_type"] != "alias":
            continue
        internal_mappings.append(
            InternalStratigraphyIdentifierMapping(
                source_system=DataSystem(mapping["source_system"]),
                target_system=DataSystem(mapping["source_system"]),
                mapping_type=MappingType.stratigraphy,
                relation_type=InternalRelationType.alias,
                source_id=mapping["source_id"],
                source_uuid=mapping.get("source_uuid"),
                target_id=primary_source_by_target[mapping["target_id"]],
                target_uuid=None,
            )
        )

    return InternalStratigraphyMappings(root=internal_mappings)
