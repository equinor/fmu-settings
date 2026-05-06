"""Tests for validators in the .fmu mapping models."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from fmu.datamodels.context.mappings import (
    DataSystem,
    MappingType,
    RelationType,
    StratigraphyMappings,
    WellboreMappings,
)

import fmu.settings.models.mappings as mappings_model
from fmu.settings.models.mappings import (
    InternalBaseMapping,
    InternalIdentifierMapping,
    InternalMappings,
    InternalRelationType,
    InternalStratigraphyIdentifierMapping,
    InternalStratigraphyMappings,
    InternalWellboreIdentifierMapping,
    InternalWellboreMappings,
)


def create_stratigraphy_mapping(
    *,
    source_system: DataSystem = DataSystem.rms,
    target_system: DataSystem = DataSystem.rms,
    relation_type: InternalRelationType = InternalRelationType.primary,
    source_id: str = "TopVolantis",
    target_id: str | None = "TopVolantis",
) -> InternalStratigraphyIdentifierMapping:
    """Build an internal .fmu stratigraphy mapping with sensible defaults."""
    return InternalStratigraphyIdentifierMapping(
        source_system=source_system,
        target_system=target_system,
        relation_type=relation_type,
        source_id=source_id,
        target_id=target_id,
    )


def create_wellbore_mapping(
    *,
    source_system: DataSystem = DataSystem.rms,
    target_system: DataSystem = DataSystem.rms,
    relation_type: InternalRelationType = InternalRelationType.primary,
    source_id: str = "30_9-B-21_C",
    target_id: str | None = "30_9-B-21_C",
) -> InternalWellboreIdentifierMapping:
    """Build an internal .fmu wellbore mapping with sensible defaults."""
    return InternalWellboreIdentifierMapping(
        source_system=source_system,
        target_system=target_system,
        relation_type=relation_type,
        source_id=source_id,
        target_id=target_id,
    )


@pytest.mark.parametrize(
    "relation_type", [InternalRelationType.primary, InternalRelationType.alias]
)
def test_internal_base_mapping_allows_same_system_primary_and_alias(
    relation_type: InternalRelationType,
) -> None:
    """Same-system primary and alias relations are allowed."""
    InternalBaseMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.rms,
        mapping_type=MappingType.stratigraphy,
        relation_type=relation_type,
    )


@pytest.mark.parametrize(
    "relation_type", [InternalRelationType.primary, InternalRelationType.unmappable]
)
def test_internal_base_mapping_allows_cross_system_primary_and_unmappable(
    relation_type: InternalRelationType,
) -> None:
    """Cross-system primary and unmappable relations are allowed."""
    InternalBaseMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        mapping_type=MappingType.stratigraphy,
        relation_type=relation_type,
    )


def test_internal_base_mapping_rejects_same_system_unmappable() -> None:
    """Unmappable is only valid for cross-system mappings."""
    with pytest.raises(
        ValueError,
        match="Same-system mapping cannot use relation_type 'unmappable'",
    ):
        InternalBaseMapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.rms,
            mapping_type=MappingType.stratigraphy,
            relation_type=InternalRelationType.unmappable,
        )


def test_internal_base_mapping_rejects_cross_system_alias() -> None:
    """Alias is only valid for same-system mappings."""
    with pytest.raises(
        ValueError,
        match="Cross-system mapping cannot use relation_type 'alias'",
    ):
        InternalBaseMapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.smda,
            mapping_type=MappingType.stratigraphy,
            relation_type=InternalRelationType.alias,
        )


def test_internal_identifier_mapping_ids_not_empty_strings() -> None:
    """Ensure that validation fails if a mapping identifier is an empty string."""
    with pytest.raises(ValueError, match="An identifier cannot be an empty string"):
        InternalIdentifierMapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.smda,
            mapping_type=MappingType.stratigraphy,
            relation_type=InternalRelationType.primary,
            source_id="",
            target_id="foo",
        )


def test_internal_identifier_mapping_strips_surrounding_whitespace_from_ids() -> None:
    """Source and target identifiers are stripped when they contain padding."""
    mapping = create_stratigraphy_mapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        relation_type=InternalRelationType.primary,
        source_id="  TopVolantis  ",
        target_id="  VOLANTIS GP. Top  ",
    )

    assert mapping.source_id == "TopVolantis"
    assert mapping.target_id == "VOLANTIS GP. Top"


def test_internal_identifier_mapping_allows_same_system_primary_mapping_to_itself() -> (
    None
):
    """Same-system primary mappings must map an identifier to itself."""
    mapping = create_stratigraphy_mapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.rms,
        relation_type=InternalRelationType.primary,
        source_id="TopVolantis",
        target_id="TopVolantis",
    )

    assert mapping.source_id == mapping.target_id


def test_internal_identifier_mapping_rejects_same_system_primary_to_other_id() -> None:
    """Same-system primary mappings cannot map an identifier to another one."""
    with pytest.raises(
        ValueError,
        match=(
            "Same-system primary mapping must have matching source_id and "
            "target_id; use relation_type='alias' if they should differ"
        ),
    ):
        create_stratigraphy_mapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.rms,
            relation_type=InternalRelationType.primary,
            source_id="TopVolantis",
            target_id="TopVolon",
        )


def test_internal_identifier_mapping_allows_same_system_alias() -> None:
    """Same-system aliases can point to a primary identifier."""
    mapping = create_stratigraphy_mapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.rms,
        relation_type=InternalRelationType.alias,
        source_id="TOP_VOLANTIS",
        target_id="TopVolantis",
    )

    assert mapping.source_id == "TOP_VOLANTIS"
    assert mapping.target_id == "TopVolantis"


def test_internal_identifier_mapping_rejects_same_system_alias_mapping_to_itself() -> (
    None
):
    """Same-system aliases must point to a different identifier."""
    with pytest.raises(
        ValueError,
        match=(
            "Same-system alias mapping must have different source_id and "
            "target_id; use relation_type='primary' if they should match"
        ),
    ):
        create_stratigraphy_mapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.rms,
            relation_type=InternalRelationType.alias,
            source_id="TopVolantis",
            target_id="TopVolantis",
        )


def test_internal_identifier_mapping_rejects_same_system_unmappable() -> None:
    """Unmappable relations are not valid for same-system mappings."""
    with pytest.raises(
        ValueError,
        match="Same-system mapping cannot use relation_type 'unmappable'",
    ):
        InternalIdentifierMapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.rms,
            mapping_type=MappingType.stratigraphy,
            relation_type=InternalRelationType.unmappable,
            source_id="NoMatch",
        )


def test_internal_identifier_mapping_rejects_cross_system_alias() -> None:
    """Alias relations are not valid for internal .fmu cross-system mappings."""
    with pytest.raises(
        ValueError,
        match="Cross-system mapping cannot use relation_type 'alias'",
    ):
        create_stratigraphy_mapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.smda,
            relation_type=InternalRelationType.alias,
            source_id="TOP_VOLANTIS",
            target_id="VOLANTIS GP. Top",
        )


def test_internal_identifier_mapping_allows_unmappable_without_target() -> None:
    """An unmappable relation can omit target identifier fields."""
    mapping = InternalIdentifierMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        mapping_type=MappingType.stratigraphy,
        relation_type=InternalRelationType.unmappable,
        source_id="NoMatch",
    )

    assert mapping.target_id is None
    assert mapping.target_uuid is None


def test_internal_identifier_mapping_allows_explicit_none_target_for_unmappable() -> (
    None
):
    """An unmappable relation also accepts an explicit null target identifier."""
    mapping = InternalIdentifierMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        mapping_type=MappingType.stratigraphy,
        relation_type=InternalRelationType.unmappable,
        source_id="NoMatch",
        target_id=None,
    )

    assert mapping.target_id is None


def test_internal_identifier_mapping_rejects_blank_target_id() -> None:
    """Target identifiers cannot be blank when provided."""
    with pytest.raises(ValueError, match="An identifier cannot be an empty string"):
        create_stratigraphy_mapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.smda,
            relation_type=InternalRelationType.primary,
            source_id="TopVolantis",
            target_id="   ",
        )


@pytest.mark.parametrize(
    ("target_system", "relation_type"),
    [
        (DataSystem.rms, InternalRelationType.primary),
        (DataSystem.rms, InternalRelationType.alias),
        (DataSystem.smda, InternalRelationType.primary),
    ],
)
def test_internal_identifier_mapping_requires_target_id_for_non_unmappable_relations(
    target_system: DataSystem,
    relation_type: InternalRelationType,
) -> None:
    """All non-unmappable mappings require a target identifier."""
    with pytest.raises(
        ValueError,
        match="target_id is required unless relation_type is 'unmappable'",
    ):
        InternalIdentifierMapping(
            source_system=DataSystem.rms,
            target_system=target_system,
            mapping_type=MappingType.stratigraphy,
            relation_type=relation_type,
            source_id="TopVolantis",
        )


def test_internal_identifier_mapping_rejects_target_for_unmappable_relation() -> None:
    """Unmappable relations must not carry target identifier fields."""
    with pytest.raises(ValueError, match="Unmappable mapping cannot define"):
        InternalIdentifierMapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.smda,
            mapping_type=MappingType.stratigraphy,
            relation_type=InternalRelationType.unmappable,
            source_id="NoMatch",
            target_id="VOLANTIS GP. Top",
        )


def test_internal_identifier_mapping_rejects_target_uuid_for_unmappable_relation() -> (
    None
):
    """Unmappable relations must not carry target UUID fields."""
    with pytest.raises(ValueError, match="Unmappable mapping cannot define"):
        InternalIdentifierMapping(
            source_system=DataSystem.rms,
            target_system=DataSystem.smda,
            mapping_type=MappingType.stratigraphy,
            relation_type=InternalRelationType.unmappable,
            source_id="NoMatch",
            target_uuid=uuid4(),
        )


def test_internal_mappings_defaults_to_empty_collections() -> None:
    """The .fmu mappings file model defaults to empty mapping collections."""
    mappings = InternalMappings()

    assert mappings.stratigraphy == InternalStratigraphyMappings(root=[])
    assert mappings.wellbore == InternalWellboreMappings(root=[])


def test_internal_stratigraphy_mappings_allow_empty_collection() -> None:
    """Stratigraphy collections can be empty when no mappings exist yet."""
    mappings = InternalStratigraphyMappings(root=[])

    assert list(mappings) == []
    assert len(mappings) == 0


def test_internal_stratigraphy_mappings_allow_valid_collection() -> None:
    """Stratigraphy collections allow valid mappings."""
    primary = create_stratigraphy_mapping()
    alias = create_stratigraphy_mapping(
        relation_type=InternalRelationType.alias,
        source_id="TOP_VOLANTIS",
        target_id="TopVolantis",
    )
    mapped = create_stratigraphy_mapping(
        target_system=DataSystem.smda,
        target_id="VOLANTIS GP. Top",
    )
    mappings = InternalStratigraphyMappings(root=[primary, alias, mapped])
    expected = [primary, alias, mapped]

    assert mappings.root == expected


def test_internal_stratigraphy_mappings_support_dunder_methods() -> None:
    """Stratigraphy collections support the expected dunder methods."""
    primary = create_stratigraphy_mapping()
    alias = create_stratigraphy_mapping(
        relation_type=InternalRelationType.alias,
        source_id="TOP_VOLANTIS",
        target_id="TopVolantis",
    )
    mapped = create_stratigraphy_mapping(
        target_system=DataSystem.smda,
        target_id="VOLANTIS GP. Top",
    )
    mappings = InternalStratigraphyMappings(root=[primary, alias, mapped])
    expected = [primary, alias, mapped]

    assert mappings[0] == primary
    assert list(mappings) == expected
    assert len(mappings) == len(expected)


def test_internal_stratigraphy_mappings_serializes_to_json_list() -> None:
    """InternalStratigraphyMappings serializes as a root list."""
    mappings = InternalStratigraphyMappings(root=[create_stratigraphy_mapping()])

    assert mappings.model_dump(mode="json", exclude_none=True) == [
        {
            "source_system": "rms",
            "target_system": "rms",
            "mapping_type": "stratigraphy",
            "relation_type": "primary",
            "source_id": "TopVolantis",
            "target_id": "TopVolantis",
        }
    ]


def test_internal_stratigraphy_mappings_validates_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """InternalStratigraphyMappings validates mappings through the shared helper."""
    mapping = create_stratigraphy_mapping()
    validate_collection = Mock()

    monkeypatch.setattr(
        mappings_model,
        "_validate_identifier_mappings_collection",
        validate_collection,
    )

    InternalStratigraphyMappings(root=[mapping])

    validate_collection.assert_called_once_with([mapping])


def test_validate_identifier_mappings_collection_rejects_alias_without_primary() -> (
    None
):
    """Same-system aliases must point to an existing same-system primary."""
    alias = create_stratigraphy_mapping(
        relation_type=InternalRelationType.alias,
        source_id="TOP_VOLANTIS",
        target_id="TopVolantis",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Same-system alias mappings must point to an existing "
            "same-system primary source_id"
        ),
    ):
        mappings_model._validate_identifier_mappings_collection([alias])


def test_validate_collection_rejects_cross_system_alias_sources() -> None:
    """Cross-system mappings must use same-system primary source identifiers."""
    primary = create_stratigraphy_mapping()
    alias = create_stratigraphy_mapping(
        relation_type=InternalRelationType.alias,
        source_id="TOP_VOLANTIS",
        target_id="TopVolantis",
    )
    mapped_alias = create_stratigraphy_mapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        relation_type=InternalRelationType.primary,
        source_id="TOP_VOLANTIS",
        target_id="VOLANTIS GP. Top",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Cross-system mappings must use a source_id that is defined "
            "as a same-system primary"
        ),
    ):
        mappings_model._validate_identifier_mappings_collection(
            [primary, alias, mapped_alias]
        )


def test_validate_collection_rejects_multiple_cross_system_outcomes() -> None:
    """A same-system primary identifier can only have one outcome per target system."""
    primary = create_stratigraphy_mapping()
    mapped = create_stratigraphy_mapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        relation_type=InternalRelationType.primary,
        source_id="TopVolantis",
        target_id="VOLANTIS GP. Top",
    )
    unmappable = create_stratigraphy_mapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        relation_type=InternalRelationType.unmappable,
        source_id="TopVolantis",
        target_id=None,
    )

    with pytest.raises(
        ValueError,
        match=("A source_id can only have one cross-system mapping per target system"),
    ):
        mappings_model._validate_identifier_mappings_collection(
            [primary, mapped, unmappable]
        )


def test_validate_collection_rejects_reused_same_system_source_id() -> None:
    """A source_id cannot be both a primary and an alias in the same collection."""
    primary = create_stratigraphy_mapping()
    other_primary = create_stratigraphy_mapping(
        source_id="TopVolon",
        target_id="TopVolon",
    )
    conflicting_alias = create_stratigraphy_mapping(
        relation_type=InternalRelationType.alias,
        source_id="TopVolantis",
        target_id="TopVolon",
    )

    with pytest.raises(
        ValueError,
        match=("Same-system mappings cannot reuse the same source_id"),
    ):
        mappings_model._validate_identifier_mappings_collection(
            [primary, other_primary, conflicting_alias]
        )


def test_validate_identifier_mappings_collection_allows_multiple_target_systems() -> (
    None
):
    """A primary source identifier can map once to each target system."""
    primary = create_stratigraphy_mapping()
    smda_mapping = create_stratigraphy_mapping(
        target_system=DataSystem.smda,
        target_id="VOLANTIS GP. Top",
    )
    simulator_mapping = create_stratigraphy_mapping(
        target_system=DataSystem.simulator,
        target_id="TopVolantis",
    )

    mappings_model._validate_identifier_mappings_collection(
        [primary, smda_mapping, simulator_mapping]
    )


@pytest.mark.parametrize(
    ("target_system", "target_id"),
    [
        (DataSystem.simulator, "B21C"),
        (DataSystem.smda, "NO 30/9-B-21 C"),
        (DataSystem.pdm, "30/9-B-21 C"),
    ],
)
def test_internal_wellbore_mapping_supports_expected_target_systems(
    target_system: DataSystem, target_id: str
) -> None:
    """Ensure wellbore mappings can target the supported systems."""
    mapping = create_wellbore_mapping(
        source_system=DataSystem.rms,
        target_system=target_system,
        relation_type=InternalRelationType.primary,
        source_id="30_9-B-21_C",
        target_id=target_id,
    )

    assert mapping.target_system == target_system
    assert mapping.target_id == target_id


def test_internal_wellbore_mappings_allow_empty_collection() -> None:
    """Wellbore collections can be empty when no mappings exist yet."""
    mappings = InternalWellboreMappings(root=[])

    assert list(mappings) == []
    assert len(mappings) == 0


def test_internal_wellbore_mappings_allow_valid_collection() -> None:
    """Wellbore collections allow valid mappings."""
    primary = create_wellbore_mapping()
    simulator_target = create_wellbore_mapping(
        target_system=DataSystem.simulator,
        target_id="B21C",
    )
    pdm_target = create_wellbore_mapping(
        target_system=DataSystem.pdm,
        target_id="30/9-B-21 C",
    )
    mappings = InternalWellboreMappings(root=[primary, simulator_target, pdm_target])
    expected = [primary, simulator_target, pdm_target]

    assert mappings.root == expected


def test_internal_wellbore_mappings_support_dunder_methods() -> None:
    """Wellbore collections support the expected dunder methods."""
    primary = create_wellbore_mapping()
    simulator_target = create_wellbore_mapping(
        target_system=DataSystem.simulator,
        target_id="B21C",
    )
    pdm_target = create_wellbore_mapping(
        target_system=DataSystem.pdm,
        target_id="30/9-B-21 C",
    )
    mappings = InternalWellboreMappings(root=[primary, simulator_target, pdm_target])
    expected = [primary, simulator_target, pdm_target]

    assert mappings[0] == primary
    assert list(mappings) == expected
    assert len(mappings) == len(expected)


def test_to_datamodels_identifier_mapping_payloads_drops_internal_only_mappings() -> (
    None
):
    """Only cross-system primary mappings are returned as datamodels payloads."""
    primary = create_stratigraphy_mapping()
    alias = create_stratigraphy_mapping(
        source_id="TopVOLANTIS",
        target_id="TopVolantis",
        relation_type=InternalRelationType.alias,
    )
    unmappable = create_stratigraphy_mapping(
        target_system=DataSystem.smda,
        target_id=None,
        relation_type=InternalRelationType.unmappable,
    )

    payloads = mappings_model._to_datamodels_identifier_mapping_payloads(
        [primary, alias, unmappable]
    )

    assert payloads == []


def test_to_datamodels_identifier_mapping_payloads_expands_aliases_to_targets() -> None:
    """Same-system aliases are expanded to matching cross-system primary mappings."""
    primary = create_stratigraphy_mapping()
    alias = create_stratigraphy_mapping(
        source_id="TopVOLANTIS",
        target_id="TopVolantis",
        relation_type=InternalRelationType.alias,
    )
    smda_mapping = create_stratigraphy_mapping(
        target_system=DataSystem.smda,
        target_id="VOLANTIS GP. Top",
    )
    simulator_mapping = create_stratigraphy_mapping(
        target_system=DataSystem.simulator,
        target_id="TopVolantis",
    )

    payloads = mappings_model._to_datamodels_identifier_mapping_payloads(
        [primary, alias, smda_mapping, simulator_mapping]
    )

    assert payloads == [
        {
            "source_system": DataSystem.rms,
            "target_system": DataSystem.smda,
            "mapping_type": MappingType.stratigraphy,
            "relation_type": RelationType.primary,
            "source_id": "TopVolantis",
            "source_uuid": None,
            "target_id": "VOLANTIS GP. Top",
            "target_uuid": None,
        },
        {
            "source_system": DataSystem.rms,
            "target_system": DataSystem.smda,
            "mapping_type": MappingType.stratigraphy,
            "relation_type": RelationType.alias,
            "source_id": "TopVOLANTIS",
            "source_uuid": None,
            "target_id": "VOLANTIS GP. Top",
            "target_uuid": None,
        },
        {
            "source_system": DataSystem.rms,
            "target_system": DataSystem.simulator,
            "mapping_type": MappingType.stratigraphy,
            "relation_type": RelationType.primary,
            "source_id": "TopVolantis",
            "source_uuid": None,
            "target_id": "TopVolantis",
            "target_uuid": None,
        },
        {
            "source_system": DataSystem.rms,
            "target_system": DataSystem.simulator,
            "mapping_type": MappingType.stratigraphy,
            "relation_type": RelationType.alias,
            "source_id": "TopVOLANTIS",
            "source_uuid": None,
            "target_id": "TopVolantis",
            "target_uuid": None,
        },
    ]


def test_to_datamodels_identifier_mapping_payloads_preserves_relevant_uuids() -> None:
    """Alias payloads use the alias source UUID and cross-system target UUID."""
    alias_source_uuid = uuid4()
    target_uuid = uuid4()
    alias = InternalStratigraphyIdentifierMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.rms,
        relation_type=InternalRelationType.alias,
        source_id="TopVOLANTIS",
        source_uuid=alias_source_uuid,
        target_id="TopVolantis",
    )
    smda_mapping = InternalStratigraphyIdentifierMapping(
        source_system=DataSystem.rms,
        target_system=DataSystem.smda,
        relation_type=InternalRelationType.primary,
        source_id="TopVolantis",
        target_id="VOLANTIS GP. Top",
        target_uuid=target_uuid,
    )

    payloads = mappings_model._to_datamodels_identifier_mapping_payloads(
        [alias, smda_mapping]
    )

    assert payloads[1]["source_uuid"] == alias_source_uuid
    assert payloads[1]["target_uuid"] == target_uuid


def test_internal_stratigraphy_mappings_converts_to_datamodels_mappings() -> None:
    """Internal .fmu mappings convert to fmu-datamodels StratigraphyMappings."""
    mappings = InternalStratigraphyMappings(
        root=[
            create_stratigraphy_mapping(),
            create_stratigraphy_mapping(
                source_id="TopVOLANTIS",
                target_id="TopVolantis",
                relation_type=InternalRelationType.alias,
            ),
            create_stratigraphy_mapping(
                target_id="VOLANTIS GP. Top",
                target_system=DataSystem.smda,
            ),
            create_stratigraphy_mapping(source_id="Seabase", target_id="Seabase"),
            create_stratigraphy_mapping(
                source_id="Seabase",
                target_id=None,
                relation_type=InternalRelationType.unmappable,
                target_system=DataSystem.smda,
            ),
        ]
    )

    converted = mappings.to_stratigraphy_mappings()

    assert isinstance(converted, StratigraphyMappings)
    assert converted.model_dump(mode="json", exclude_none=True) == [
        {
            "source_system": "rms",
            "target_system": "smda",
            "mapping_type": "stratigraphy",
            "relation_type": "primary",
            "source_id": "TopVolantis",
            "target_id": "VOLANTIS GP. Top",
        },
        {
            "source_system": "rms",
            "target_system": "smda",
            "mapping_type": "stratigraphy",
            "relation_type": "alias",
            "source_id": "TopVOLANTIS",
            "target_id": "VOLANTIS GP. Top",
        },
    ]


def test_internal_wellbore_mappings_converts_to_datamodels_mappings() -> None:
    """Internal .fmu mappings convert to fmu-datamodels WellboreMappings."""
    mappings = InternalWellboreMappings(
        root=[
            create_wellbore_mapping(),
            create_wellbore_mapping(
                source_id="30_9-B-21C",
                target_id="30_9-B-21_C",
                relation_type=InternalRelationType.alias,
            ),
            create_wellbore_mapping(
                target_system=DataSystem.simulator,
                target_id="B21C",
            ),
        ]
    )

    converted = mappings.to_wellbore_mappings()

    assert isinstance(converted, WellboreMappings)
    assert converted.model_dump(mode="json", exclude_none=True) == [
        {
            "source_system": "rms",
            "target_system": "simulator",
            "mapping_type": "wellbore",
            "relation_type": "primary",
            "source_id": "30_9-B-21_C",
            "target_id": "B21C",
        },
        {
            "source_system": "rms",
            "target_system": "simulator",
            "mapping_type": "wellbore",
            "relation_type": "alias",
            "source_id": "30_9-B-21C",
            "target_id": "B21C",
        },
    ]
