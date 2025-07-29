"""Contains models used for representing mappings within FMU."""

from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, RootModel

from fmu.datamodels.enums import Content  # type: ignore

from ._enums import (
    DataEntrySource,
    MappingType,
    RelationType,
    TargetSystem,
)


class Source(BaseModel):
    name: str
    data_entry_source: DataEntrySource


class BaseMapping(BaseModel):
    """The base mapping containing the fields all mappings should contain.

    These fields will be contained in every individual mapping entry.
    """

    source_system: str
    target_system: TargetSystem
    mapping_type: MappingType


class IdentifierMapping(BaseMapping):
    """Base class for a one-to-one or many-to-one mapping of identifiers.

    This mapping represents takes some identifier from one source and correlates it to
    an identifier in a target. Most often this target will be some official masterdata
    store like SMDA.
    """

    source_id: str
    target_id: str
    target_uuid: UUID


class StratigraphyMapping(IdentifierMapping):
    """Represents a stratigraphy mapping.

    This is a mapping from stratigraphic aliases identifiers to an official
    identifier.
    """

    mapping_type: Literal[MappingType.stratigraphy] = MappingType.stratigraphy


class WellMapping(IdentifierMapping):
    """Represents a well mapping.

    This is a mapping from well aliases identifiers to an official
    identifier.
    """

    mapping_type: Literal[MappingType.well] = MappingType.well


class FaultMapping(IdentifierMapping):
    """Represents a fault mapping.

    This is a mapping from fault aliases identifiers to an official
    identifier.
    """

    mapping_type: Literal[MappingType.well]


class EntityReference(BaseModel):
    """Represents one entity we wish to related to naother entity.

    This is typically an object exported by dataio.
    """

    name: str
    uuid: UUID
    content: Content
    relative_path: Path
    absolute_path: Path


class RelationshipMapping(BaseMapping):
    """Base class for a mapping that represents a relationship between two entities."""

    source_entity: EntityReference
    target_entity: EntityReference
    relation_type: RelationType


class ParentChildMapping(BaseMapping):
    """A mapping between a child and their parent."""


class HierarchicalMapping(RelationshipMapping):
    """A mapping that contains a hierarchy."""


class Mappings(BaseModel):
    """A list of mappings under a mappings key in metadata or in a file on disk."""

    items: list[BaseMapping]


class OrderedMappings(Mappings):
    """Items in this list imply an ordering that is important in some context."""


MappingFile = RootModel[Mappings]
"""Represents a list of mappings contained in a text file."""
