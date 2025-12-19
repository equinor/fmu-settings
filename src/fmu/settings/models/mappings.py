"""Model for the mappings.json file."""

from typing import Any

from pydantic import BaseModel, Field

from fmu.datamodels.context.mappings import StratigraphyMappings


class Mappings(BaseModel):
    """Represents the mappings file in a .fmu directory."""

    stratigraphy: StratigraphyMappings = Field(
        default_factory=lambda: StratigraphyMappings(root=[])
    )
    """Stratigraphy mappings in the mappings file."""

    # Todo: Add wells model
    wells: list[Any] = Field(default_factory=list)
    """Well mappings in the mappings file."""
