"""Model for the mappings.json file."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_serializer, model_validator

from fmu.datamodels.context.mappings import (
    AnyIdentifierMapping,
    DataSystem,
    MappingType,
    RelationType,
    StratigraphyMappings,
)


class Mappings(BaseModel):
    """Represents the mappings file in a .fmu directory."""

    stratigraphy: StratigraphyMappings = Field(
        default_factory=lambda: StratigraphyMappings(root=[])
    )
    """Stratigraphy mappings in the mappings file."""

    # Todo: Add wells model
    wells: list[Any] = Field(default_factory=list)
    """Well mappings in the mappings file."""


class MappingGroup(BaseModel):
    """A mapping group containing related mappings with a shared target context.

    This is a view of the data for GUI display purposes, not how it's stored.
    Groups mappings that share target_id, target_uuid (if set), mapping_type,
    target_system, and source_system.
    """

    target_id: str
    target_uuid: UUID | None = None
    mapping_type: MappingType
    target_system: DataSystem
    source_system: DataSystem
    mappings: list[AnyIdentifierMapping]

    @model_validator(mode="after")
    def validate_group(self) -> "MappingGroup":
        """Ensure mappings align with the group target/source and shared fields."""
        if not self.mappings:
            return self

        primary_count = sum(
            1
            for mapping in self.mappings
            if mapping.relation_type == RelationType.primary
        )
        if primary_count > 1:
            raise ValueError("MappingGroup must contain at most one primary mapping.")

        for mapping in self.mappings:
            if mapping.target_id != self.target_id:
                raise ValueError(
                    "All mappings in MappingGroup must share target_id "
                    f"'{self.target_id}'."
                )
            if mapping.mapping_type != self.mapping_type:
                raise ValueError(
                    "All mappings in MappingGroup must share mapping_type "
                    f"'{self.mapping_type}'."
                )
            if mapping.target_system != self.target_system:
                raise ValueError(
                    "All mappings in MappingGroup must share target_system "
                    f"'{self.target_system}'."
                )
            if mapping.source_system != self.source_system:
                raise ValueError(
                    "All mappings in MappingGroup must share source_system "
                    f"'{self.source_system}'."
                )

            if (
                mapping.target_uuid is not None
                and self.target_uuid is not None
                and mapping.target_uuid != self.target_uuid
            ):
                raise ValueError(
                    "All mappings in MappingGroup must share target_uuid "
                    f"'{self.target_uuid}'."
                )
        return self

    @model_serializer(mode="plain")
    def serialize_for_display(self) -> dict[str, Any]:
        """Serialize to the display schema for API responses."""
        excluded_fields = {
            "source_system",
            "target_system",
            "mapping_type",
            "target_id",
            "target_uuid",
        }
        return {
            "official_name": self.target_id,
            "target_uuid": self.target_uuid,
            "mapping_type": self.mapping_type.value,
            "target_system": self.target_system.value,
            "source_system": self.source_system.value,
            "mappings": [
                {
                    key: value
                    for key, value in mapping.model_dump().items()
                    if key not in excluded_fields
                }
                for mapping in self.mappings
            ],
        }
