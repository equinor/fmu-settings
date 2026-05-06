"""Models for the mappings.json file."""

from collections.abc import Iterator, Sequence
from enum import StrEnum
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, RootModel, field_validator, model_validator

from fmu.datamodels.context.mappings import (
    DataSystem,
    MappingType,
    RelationType,
    StratigraphyIdentifierMapping,
    StratigraphyMappings,
    WellboreIdentifierMapping,
    WellboreMappings,
)


class InternalRelationType(StrEnum):
    """The kind of relation this internal .fmu mapping represents."""

    primary = "primary"
    """The main source identifier to use for this mapping."""

    alias = "alias"
    """Alias of a primary identifier."""

    unmappable = "unmappable"
    """A source identifier that has been reviewed and cannot be mapped."""


class InternalBaseMapping(BaseModel):
    """Base fields for internal mappings stored in .fmu/mappings.json.

    Unlike the fmu-datamodels mapping models, internal mappings may represent
    same-system relationships and unmappable source identifiers.
    """

    source_system: DataSystem
    target_system: DataSystem
    mapping_type: MappingType
    relation_type: InternalRelationType

    @model_validator(mode="after")
    def validate_relation_system_constraints(self: Self) -> Self:
        """Validate which relation types are allowed for same vs cross-system mappings.

        Same-system mappings can only be ``primary`` or ``alias``.
        Cross-system mappings can only be ``primary`` or ``unmappable``.
        """
        if self.source_system == self.target_system:
            if self.relation_type == InternalRelationType.unmappable:
                raise ValueError(
                    "Same-system mapping cannot use relation_type 'unmappable'"
                )
            return self

        if self.relation_type == InternalRelationType.alias:
            raise ValueError("Cross-system mapping cannot use relation_type 'alias'")

        return self


class InternalIdentifierMapping(InternalBaseMapping):
    """Identifier mapping stored in .fmu/mappings.json.

    The internal storage schema allows same-system primaries and aliases, and it
    allows cross-system unmappable mappings without target identifiers.
    fmu-datamodels identifier mappings only represent cross-system primary and
    alias mappings with targets.
    """

    source_id: str
    source_uuid: UUID | None = None
    target_id: str | None = None
    target_uuid: UUID | None = None

    @field_validator("source_id")
    @classmethod
    def validate_source_id_not_empty(cls, value: str) -> str:
        """Ensure source identifiers are not empty strings."""
        if not value or not value.strip():
            raise ValueError("An identifier cannot be an empty string")
        return value.strip()

    @field_validator("target_id")
    @classmethod
    def validate_target_id_not_empty(cls, value: str | None) -> str | None:
        """Ensure target identifiers are not empty strings when provided."""
        if value is None:
            return value
        if not value.strip():
            raise ValueError("An identifier cannot be an empty string")
        return value.strip()

    @model_validator(mode="after")
    def validate_relation_target_constraints(self: Self) -> Self:
        """Validate how ``source_id`` and ``target_id`` are allowed to relate.

        This means:
        - ``unmappable`` mappings must leave the target empty
        - all other mappings must provide a target
        - same-system ``primary`` mappings must use the same ``source_id`` and
          ``target_id``
        - same-system ``alias`` mappings must point to a different same-system
          ``target_id``
        """
        if self.relation_type == InternalRelationType.unmappable:
            if self.target_id is not None or self.target_uuid is not None:
                raise ValueError(
                    "Unmappable mapping cannot define target_id or target_uuid"
                )
            return self

        if self.target_id is None:
            raise ValueError(
                "target_id is required unless relation_type is 'unmappable'"
            )

        if self.source_system == self.target_system:
            if self.relation_type == InternalRelationType.primary:
                if self.source_id != self.target_id:
                    raise ValueError(
                        "Same-system primary mapping must have matching source_id "
                        "and target_id; use relation_type='alias' if they should "
                        "differ"
                    )
                return self

            if self.relation_type == InternalRelationType.alias:
                if self.source_id == self.target_id:
                    raise ValueError(
                        "Same-system alias mapping must have different source_id "
                        "and target_id; use relation_type='primary' if they should "
                        "match"
                    )
                return self

        return self


class InternalStratigraphyIdentifierMapping(InternalIdentifierMapping):
    """Stratigraphy identifier mapping stored in .fmu/mappings.json.

    Use ``to_stratigraphy_mappings()`` on the collection model when consumers
    need the fmu-datamodels mapping schema.
    """

    mapping_type: Literal[MappingType.stratigraphy] = MappingType.stratigraphy


class InternalWellboreIdentifierMapping(InternalIdentifierMapping):
    """Wellbore identifier mapping stored in .fmu/mappings.json.

    Use ``to_wellbore_mappings()`` on the collection model when consumers need
    the fmu-datamodels mapping schema.
    """

    mapping_type: Literal[MappingType.wellbore] = MappingType.wellbore


class InternalStratigraphyMappings(
    RootModel[list[InternalStratigraphyIdentifierMapping]]
):
    """Collection of stratigraphy mappings stored in .fmu/mappings.json.

    This internal model can keep same-system alias information and unmappable
    relation. Converting to fmu-datamodels drops unmappable entries and expands
    same-system aliases onto matching cross-system primary mappings.
    """

    root: list[InternalStratigraphyIdentifierMapping]

    @model_validator(mode="after")
    def validate_collection(self: Self) -> Self:
        """Ensure the mapping collection follows the allowed mapping rules."""
        _validate_identifier_mappings_collection(self.root)
        return self

    def to_stratigraphy_mappings(self: Self) -> StratigraphyMappings:
        """Convert internal .fmu mappings to fmu-datamodels StratigraphyMappings."""
        return StratigraphyMappings(
            root=[
                StratigraphyIdentifierMapping(**mapping)
                for mapping in _to_datamodels_identifier_mapping_payloads(self.root)
            ]
        )

    def __getitem__(self: Self, index: int) -> InternalStratigraphyIdentifierMapping:
        """Retrieve a stratigraphy mapping from the list by index."""
        return self.root[index]

    def __iter__(self: Self) -> Iterator[InternalStratigraphyIdentifierMapping]:  # type: ignore[override]
        """Return an iterator for the stratigraphy mappings."""
        return iter(self.root)

    def __len__(self: Self) -> int:
        """Return the number of stratigraphy mappings."""
        return len(self.root)


class InternalWellboreMappings(RootModel[list[InternalWellboreIdentifierMapping]]):
    """Collection of wellbore mappings stored in .fmu/mappings.json.

    This internal model can keep same-system alias information and unmappable
    relation. Converting to fmu-datamodels drops unmappable entries and expands
    same-system aliases onto matching cross-system primary mappings.
    """

    root: list[InternalWellboreIdentifierMapping]

    @model_validator(mode="after")
    def validate_collection(self: Self) -> Self:
        """Ensure the mapping collection follows the allowed mapping rules."""
        _validate_identifier_mappings_collection(self.root)
        return self

    def to_wellbore_mappings(self: Self) -> WellboreMappings:
        """Convert internal .fmu mappings to fmu-datamodels WellboreMappings."""
        return WellboreMappings(
            root=[
                WellboreIdentifierMapping(**mapping)
                for mapping in _to_datamodels_identifier_mapping_payloads(self.root)
            ]
        )

    def __getitem__(self: Self, index: int) -> InternalWellboreIdentifierMapping:
        """Retrieve a wellbore mapping from the list by index."""
        return self.root[index]

    def __iter__(self: Self) -> Iterator[InternalWellboreIdentifierMapping]:  # type: ignore[override]
        """Return an iterator for the wellbore mappings."""
        return iter(self.root)

    def __len__(self: Self) -> int:
        """Return the number of wellbore mappings."""
        return len(self.root)


class InternalMappings(BaseModel):
    """Represents the .fmu/mappings.json storage schema."""

    stratigraphy: InternalStratigraphyMappings = Field(
        default_factory=lambda: InternalStratigraphyMappings(root=[])
    )
    """Stratigraphy mappings in the mappings file."""

    wellbore: InternalWellboreMappings = Field(
        default_factory=lambda: InternalWellboreMappings(root=[])
    )
    """Wellbore mappings in the mappings file."""


def _validate_identifier_mappings_collection(
    mappings: Sequence[InternalIdentifierMapping],
) -> None:
    """Validate how mappings are allowed to fit together when stored internally.

    The collection must satisfy three invariants:

    - A same-system ``source_id`` can appear only once per mapping type.
      Example valid mappings::

          rms -> rms, primary, source_id="TopVolantis", target_id="TopVolantis"
          rms -> rms, alias, source_id="TOP_VOLANTIS", target_id="TopVolantis"

      Example invalid mappings::

          rms -> rms, primary, source_id="TopVolantis", target_id="TopVolantis"
          rms -> rms, alias, source_id="TopVolantis", target_id="TopVolon"

      The second mapping is invalid because ``TopVolantis`` is reused as a
      same-system ``source_id``.

    - Same-system alias mappings must point to an existing same-system primary
      mapping.
      Example valid mappings::

          rms -> rms, primary, source_id="TopVolantis", target_id="TopVolantis"
          rms -> rms, alias, source_id="TOP_VOLANTIS", target_id="TopVolantis"

      Example invalid mapping::

          rms -> rms, alias, source_id="TOP_VOLANTIS", target_id="TopVolantis"

      The alias is invalid on its own because there is no same-system primary
      mapping for ``TopVolantis``.

    - Cross-system mappings must originate from a same-system primary mapping and
      can appear only once per target system.
      Example valid mappings::

          rms -> rms, primary, source_id="TopVolantis", target_id="TopVolantis"
          rms -> smda, primary, source_id="TopVolantis", target_id="VOLANTIS GP. Top"

      Example invalid mappings::

          rms -> rms, alias, source_id="TOP_VOLANTIS", target_id="TopVolantis"
          rms -> smda, primary, source_id="TOP_VOLANTIS", target_id="VOLANTIS GP. Top"

      The cross-system mapping is invalid because it starts from an alias instead
      of a same-system primary. It is also invalid to add two ``rms -> smda``
      mappings for the same ``source_id``.
    """
    same_system_source_keys: set[tuple[DataSystem, MappingType, str]] = set()
    same_system_primary_source_keys: set[tuple[DataSystem, MappingType, str]] = set()
    same_system_aliases: list[InternalIdentifierMapping] = []
    cross_system_source_keys: set[tuple[MappingType, DataSystem, DataSystem, str]] = (
        set()
    )
    cross_system_mappings: list[InternalIdentifierMapping] = []

    for mapping in mappings:
        source_key = (
            mapping.source_system,
            mapping.mapping_type,
            mapping.source_id,
        )

        # Same-system mappings tell us which source_id is the primary and which
        # source_ids are aliases of that primary.
        if mapping.source_system == mapping.target_system:
            if source_key in same_system_source_keys:
                raise ValueError("Same-system mappings cannot reuse the same source_id")
            same_system_source_keys.add(source_key)

            if mapping.relation_type == InternalRelationType.primary:
                same_system_primary_source_keys.add(source_key)
            else:
                same_system_aliases.append(mapping)
            continue

        # A source_id can map to each target system only once.
        cross_system_key = (
            mapping.mapping_type,
            mapping.source_system,
            mapping.target_system,
            mapping.source_id,
        )
        if cross_system_key in cross_system_source_keys:
            raise ValueError(
                "A source_id can only have one cross-system mapping per target system"
            )
        cross_system_source_keys.add(cross_system_key)
        cross_system_mappings.append(mapping)

    # Every alias must point to a same-system primary source_id that already
    # exists in the collection.
    for mapping in same_system_aliases:
        primary_target_id = mapping.target_id
        assert primary_target_id is not None
        primary_target_key = (
            mapping.source_system,
            mapping.mapping_type,
            primary_target_id,
        )
        if primary_target_key not in same_system_primary_source_keys:
            raise ValueError(
                "Same-system alias mappings must point to an existing "
                "same-system primary source_id"
            )

    # Cross-system mappings are only allowed when they start from a same-system
    # primary source_id.
    for mapping in cross_system_mappings:
        primary_source_key = (
            mapping.source_system,
            mapping.mapping_type,
            mapping.source_id,
        )
        if primary_source_key not in same_system_primary_source_keys:
            raise ValueError(
                "Cross-system mappings must use a source_id that is defined "
                "as a same-system primary"
            )


def _to_datamodels_identifier_mapping_payloads(
    mappings: Sequence[InternalIdentifierMapping],
) -> list[dict[str, Any]]:
    """Convert internal mappings to fmu-datamodels identifier mapping payloads.

    Stored .fmu mappings can describe relationships inside the same system, for
    example ``rms -> rms`` primaries and aliases. Downstream consumers often need
    the regular mapping models from fmu-datamodels instead, for example
    ``rms -> smda``.

    This method first finds same-system aliases and groups them by the same-system
    primary identifier they point to. It then keeps cross-system primary mappings
    and adds matching aliases to the same cross-system target. A same-system alias
    is only included when its primary identifier also has a cross-system primary
    mapping.

    Example:
    - ``rms -> rms: TopVolantis primary TopVolantis``
    - ``rms -> rms: TopVOLANTIS alias TopVolantis``
    - ``rms -> rms: TOP_VOLANTIS alias TopVolantis``
    - ``rms -> smda: TopVolantis primary VOLANTIS GP. Top``
    - ``rms -> rms: Seabase primary Seabase``
    - ``rms -> smda: Seabase unmappable``

    becomes:
    - ``rms -> smda: TopVolantis primary VOLANTIS GP. Top``
    - ``rms -> smda: TopVOLANTIS alias VOLANTIS GP. Top``
    - ``rms -> smda: TOP_VOLANTIS alias VOLANTIS GP. Top``

    Same-system mappings and unmappable mappings are not included in the returned
    fmu-datamodels mapping payloads.
    """
    aliases_by_primary: dict[
        tuple[MappingType, DataSystem, str], list[InternalIdentifierMapping]
    ] = {}

    # Group same-system aliases by the same-system primary id they point to.
    for mapping in mappings:
        if _is_same_system_alias(mapping):
            assert mapping.target_id is not None
            aliases_by_primary.setdefault(
                _primary_key(mapping, mapping.target_id), []
            ).append(mapping)

    mapping_payloads: list[dict[str, Any]] = []

    # Keep cross-system primaries and add matching aliases to the same target.
    for mapping in mappings:
        if not _is_cross_system_primary(mapping):
            continue

        mapping_payloads.append(_to_mapping_payload(mapping))
        for alias_mapping in aliases_by_primary.get(
            _primary_key(mapping, mapping.source_id), []
        ):
            alias_payload = _to_mapping_payload(mapping)
            alias_payload.update(
                {
                    "relation_type": RelationType.alias,
                    "source_id": alias_mapping.source_id,
                    "source_uuid": alias_mapping.source_uuid,
                }
            )
            mapping_payloads.append(alias_payload)

    return mapping_payloads


def _is_same_system_alias(mapping: InternalIdentifierMapping) -> bool:
    """Return whether a mapping is a same-system alias."""
    return (
        mapping.source_system == mapping.target_system
        and mapping.relation_type == InternalRelationType.alias
        and mapping.target_id is not None
    )


def _is_cross_system_primary(mapping: InternalIdentifierMapping) -> bool:
    """Return whether a mapping is a cross-system primary with a target."""
    return (
        mapping.source_system != mapping.target_system
        and mapping.relation_type == InternalRelationType.primary
        and mapping.target_id is not None
    )


def _primary_key(
    mapping: InternalIdentifierMapping, source_id: str
) -> tuple[MappingType, DataSystem, str]:
    """Return the grouping key for mappings related to a primary source id."""
    return mapping.mapping_type, mapping.source_system, source_id


def _to_mapping_payload(mapping: InternalIdentifierMapping) -> dict[str, Any]:
    """Return a payload compatible with fmu-datamodels mapping models."""
    payload = mapping.model_dump()
    payload["relation_type"] = RelationType(mapping.relation_type.value)
    return payload
