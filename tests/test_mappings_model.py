"""Tests for mapping models."""

from uuid import UUID, uuid4

import pytest
from fmu.datamodels.context.mappings import (
    DataSystem,
    MappingType,
    RelationType,
    StratigraphyIdentifierMapping,
)
from pydantic import ValidationError

from fmu.settings.models.mappings import MappingGroup


def _make_mapping(  # noqa: PLR0913
    source_id: str,
    target_id: str,
    relation_type: RelationType,
    source_system: DataSystem = DataSystem.rms,
    target_system: DataSystem = DataSystem.smda,
    target_uuid: UUID | None = None,
) -> StratigraphyIdentifierMapping:
    return StratigraphyIdentifierMapping(
        source_system=source_system,
        target_system=target_system,
        relation_type=relation_type,
        source_id=source_id,
        target_id=target_id,
        target_uuid=target_uuid,
    )


def test_mapping_group_count_mappings_by_relation_type() -> None:
    """Tests that the count of mappings with the given relation_type is returned."""
    target_id = "Viking GP."
    primary = _make_mapping("Viking Gp", target_id, RelationType.primary)
    alias = _make_mapping("Viking gp", target_id, RelationType.alias)
    alias_two = _make_mapping("VIKING GP", target_id, RelationType.alias)
    alias_three = _make_mapping("viking.gp", target_id, RelationType.alias)
    equivalent = _make_mapping("Viking GP.", target_id, RelationType.equivalent)

    mapping_group = MappingGroup(
        target_id=target_id,
        mapping_type=MappingType.stratigraphy,
        target_system=DataSystem.smda,
        source_system=DataSystem.rms,
        mappings=[primary, alias, alias_two, alias_three, equivalent],
    )

    assert mapping_group._count_mappings_by_relation_type(RelationType.primary) == 1
    assert mapping_group._count_mappings_by_relation_type(RelationType.equivalent) == 1
    expected_alias_mappings = 3
    assert (
        mapping_group._count_mappings_by_relation_type(RelationType.alias)
        == expected_alias_mappings
    )


def test_mapping_group_serializes_without_system_and_target_fields() -> None:
    """MappingGroup serializes mappings without redundant fields."""
    target_id = "Viking GP."
    target_uuid = uuid4()
    primary = _make_mapping(
        "Viking Gp", target_id, RelationType.primary, target_uuid=target_uuid
    )
    alias = _make_mapping(
        "Viking Group", target_id, RelationType.alias, target_uuid=target_uuid
    )
    equivalent = _make_mapping(
        target_id, target_id, RelationType.equivalent, target_uuid=target_uuid
    )

    group = MappingGroup(
        target_id=target_id,
        target_uuid=target_uuid,
        mapping_type=MappingType.stratigraphy,
        target_system=DataSystem.smda,
        source_system=DataSystem.rms,
        mappings=[primary, alias, equivalent],
    )

    display_dict = group.model_dump()
    assert display_dict["official_name"] == target_id
    assert display_dict["target_uuid"] == target_uuid
    assert display_dict["mapping_type"] == "stratigraphy"
    assert display_dict["target_system"] == "smda"
    assert display_dict["source_system"] == "rms"
    for mapping in display_dict["mappings"]:
        assert "source_system" not in mapping
        assert "target_system" not in mapping
        assert "mapping_type" not in mapping
        assert "target_id" not in mapping
        assert "target_uuid" not in mapping
        assert "relation_type" in mapping
        assert "source_id" in mapping


def test_mapping_group_rejects_multiple_primary_mappings() -> None:
    """MappingGroup with more than one primary mapping raises ValidationError."""
    target_id = "Viking GP."
    primary = _make_mapping("Viking Gp", target_id, RelationType.primary)
    primary_two = _make_mapping("Viking Gp 2", target_id, RelationType.primary)
    with pytest.raises(ValidationError, match="at most one primary mapping."):
        MappingGroup(
            target_id=target_id,
            mapping_type=MappingType.stratigraphy,
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[primary, primary_two],
        )


def test_mapping_group_rejects_multiple_equivalent_mappings() -> None:
    """MappingGroup with more than one equivalent mapping raises ValidationError."""
    target_id = "Viking GP."
    equivalent = _make_mapping("Viking GP.", target_id, RelationType.equivalent)
    equivalent_two = _make_mapping("Viking GP.", target_id, RelationType.equivalent)
    with pytest.raises(ValidationError, match="at most one equivalent mapping."):
        MappingGroup(
            target_id=target_id,
            mapping_type=MappingType.stratigraphy,
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[equivalent, equivalent_two],
        )


def test_mapping_group_with_alias_requires_primary_relation() -> None:
    """MappingsGroup with alias mappings and no primary mapping raises ValidationError.

    A MappingGroup containing alias mappings will raise a ValidationError
    Error if no primary mapping exists.
    """
    target_id = "Viking GP."
    alias = _make_mapping("Viking gp", target_id, RelationType.alias)
    alias_two = _make_mapping("VIKING GP", target_id, RelationType.alias)
    equivalent = _make_mapping("Viking GP.", target_id, RelationType.equivalent)
    with pytest.raises(
        ValidationError, match="contains alias relations but no primary relation."
    ):
        MappingGroup(
            target_id=target_id,
            mapping_type=MappingType.stratigraphy,
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[alias, alias_two, equivalent],
        )


def test_mapping_group_requires_no_duplicate_mappings() -> None:
    """MappingGroup with duplicate mappings raises ValidationError."""
    target_id = "Viking GP."
    primary = _make_mapping("VIKING GP", target_id, RelationType.primary)
    alias = _make_mapping("Viking gp", target_id, RelationType.alias)
    alias_two = _make_mapping("Viking gp", target_id, RelationType.alias)
    with pytest.raises(ValidationError, match="Duplicate mapping in group:"):
        MappingGroup(
            target_id=target_id,
            mapping_type=MappingType.stratigraphy,
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[primary, alias, alias_two],
        )


def test_mapping_group_requires_shared_target_id() -> None:
    """All mappings must share the group target_id."""
    primary = _make_mapping("Viking Gp", "Viking GP.", RelationType.primary)
    different_target = _make_mapping("westeros", "Westeros", RelationType.alias)

    with pytest.raises(ValidationError, match="target_id"):
        MappingGroup(
            target_id="Viking GP.",
            mapping_type=MappingType.stratigraphy,
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[primary, different_target],
        )


def test_mapping_group_requires_shared_target_system() -> None:
    """All mappings must share the group target_system."""
    primary = _make_mapping("Viking Gp", "Viking GP.", RelationType.primary)
    different_target_system = _make_mapping(
        "Viking Gp 2",
        "Viking GP.",
        RelationType.alias,
        target_system=DataSystem.fmu,
    )

    with pytest.raises(ValidationError, match="target_system"):
        MappingGroup(
            target_id="Viking GP.",
            mapping_type=MappingType.stratigraphy,
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[primary, different_target_system],
        )


def test_mapping_group_requires_shared_source_system() -> None:
    """All mappings must share the group source_system."""
    primary = _make_mapping("Viking Gp", "Viking GP.", RelationType.primary)
    different_source_system = _make_mapping(
        "Viking Gp 2",
        "Viking GP.",
        RelationType.alias,
        source_system=DataSystem.fmu,
    )

    with pytest.raises(ValidationError, match="source_system"):
        MappingGroup(
            target_id="Viking GP.",
            mapping_type=MappingType.stratigraphy,
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[primary, different_source_system],
        )
