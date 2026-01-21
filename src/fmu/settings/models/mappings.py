"""Model for the mappings.json file."""

from typing import Any

from pydantic import BaseModel, Field, model_validator

from fmu.datamodels.context.mappings import (
    AnyIdentifierMapping,
    DataSystem,
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
    """A mapping group containing a primary mapping and its related mappings.

    This is a view of the data for GUI display purposes, not how it's stored.
    Groups all mappings (primary, aliases, equivalents) that share the same target.

    Validates that all mappings share the group target_id, target_system,
    and source_system.
    """

    target_id: str
    target_system: DataSystem
    source_system: DataSystem
    mappings: list[AnyIdentifierMapping]

    @property
    def primary(self) -> AnyIdentifierMapping | None:
        """Get the primary mapping.

        Takes the first primary, which should be the only one.
        """
        primaries = [
            m for m in self.mappings if m.relation_type == RelationType.primary
        ]
        return primaries[0] if primaries else None

    @property
    def aliases(self) -> list[AnyIdentifierMapping]:
        """Get all alias mappings."""
        return [m for m in self.mappings if m.relation_type == RelationType.alias]

    @property
    def equivalents(self) -> list[AnyIdentifierMapping]:
        """Get all equivalent mappings."""
        return [m for m in self.mappings if m.relation_type == RelationType.equivalent]

    @model_validator(mode="after")
    def validate_group(self) -> "MappingGroup":
        """Ensure mappings align with the group target/source and primary count."""
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
        return self

    def to_display_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for display."""
        return {
            "official_name": self.target_id,
            "target_system": self.target_system.value,
            "source_system": self.source_system.value,
            "primary_source": self.primary.source_id if self.primary else None,
            "aliases": [m.source_id for m in self.aliases],
            "equivalents": [m.source_id for m in self.equivalents],
        }
