"""Tests for mapping models."""

import pytest
from fmu.datamodels.context.mappings import (
    DataSystem,
    RelationType,
    StratigraphyIdentifierMapping,
)
from pydantic import ValidationError

from fmu.settings.models.mappings import MappingGroup


def _make_mapping(
    source_id: str,
    target_id: str,
    relation_type: RelationType,
    source_system: DataSystem = DataSystem.rms,
    target_system: DataSystem = DataSystem.smda,
) -> StratigraphyIdentifierMapping:
    return StratigraphyIdentifierMapping(
        source_system=source_system,
        target_system=target_system,
        relation_type=relation_type,
        source_id=source_id,
        target_id=target_id,
    )


def test_mapping_group_valid_and_display_dict() -> None:
    """MappingGroup groups mappings with a single primary and shared systems."""
    target_id = "Viking GP."
    primary = _make_mapping("Viking Gp", target_id, RelationType.primary)
    alias = _make_mapping("Viking Group", target_id, RelationType.alias)
    equivalent = _make_mapping(target_id, target_id, RelationType.equivalent)

    group = MappingGroup(
        target_id=target_id,
        target_system=DataSystem.smda,
        source_system=DataSystem.rms,
        mappings=[primary, alias, equivalent],
    )

    assert group.primary == primary
    assert group.aliases == [alias]
    assert group.equivalents == [equivalent]
    assert group.to_display_dict() == {
        "official_name": target_id,
        "target_system": "smda",
        "source_system": "rms",
        "primary_source": "Viking Gp",
        "aliases": ["Viking Group"],
        "equivalents": [target_id],
    }


def test_mapping_group_rejects_multiple_primary_mappings() -> None:
    """MappingGroup allows at most one primary mapping."""
    target_id = "Viking GP."
    primary = _make_mapping("Viking Gp", target_id, RelationType.primary)
    primary_two = _make_mapping("Viking Gp 2", target_id, RelationType.primary)
    with pytest.raises(ValidationError, match="at most one primary"):
        MappingGroup(
            target_id=target_id,
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[primary, primary_two],
        )


def test_mapping_group_requires_shared_target_id() -> None:
    """All mappings must share the group target_id."""
    primary = _make_mapping("Viking Gp", "Viking GP.", RelationType.primary)
    different_target = _make_mapping("westeros", "Westeros", RelationType.alias)

    with pytest.raises(ValidationError, match="target_id"):
        MappingGroup(
            target_id="Viking GP.",
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
            target_system=DataSystem.smda,
            source_system=DataSystem.rms,
            mappings=[primary, different_source_system],
        )
