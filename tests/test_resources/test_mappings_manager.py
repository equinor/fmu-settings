"""Tests for MappingsManager."""

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from uuid import UUID

import pytest
from fmu.datamodels.context.mappings import (
    DataSystem,
    MappingType,
    StratigraphyMappings,
    WellboreMappings,
)

from fmu.settings._drogon import GLOBAL_CONFIG_STRATIGRAPHY
from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.mappings_manager import MappingsManager
from fmu.settings.models._enums import ChangeType
from fmu.settings.models.diff import ListFieldDiff, ListUpdatedEntry
from fmu.settings.models.mappings import (
    InternalMappings,
    InternalRelationType,
    InternalStratigraphyIdentifierMapping,
    InternalStratigraphyMappings,
    InternalWellboreIdentifierMapping,
    InternalWellboreMappings,
)

if TYPE_CHECKING:
    from fmu.settings.models.change_info import ChangeInfo
    from fmu.settings.models.log import Log


def _stratigraphy_mappings(
    source_id: str,
    target_id: str,
    *aliases: str,
    target_uuid: UUID | None = None,
) -> InternalStratigraphyMappings:
    return InternalStratigraphyMappings(
        root=[
            InternalStratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.rms,
                relation_type=InternalRelationType.primary,
                source_id=source_id,
                target_id=source_id,
            ),
            *[
                InternalStratigraphyIdentifierMapping(
                    source_system=DataSystem.rms,
                    target_system=DataSystem.rms,
                    relation_type=InternalRelationType.alias,
                    source_id=alias,
                    target_id=source_id,
                )
                for alias in aliases
            ],
            InternalStratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.smda,
                relation_type=InternalRelationType.primary,
                source_id=source_id,
                target_id=target_id,
                target_uuid=target_uuid,
            ),
        ]
    )


def _wellbore_mappings(source_id: str, target_id: str) -> InternalWellboreMappings:
    return InternalWellboreMappings(
        root=[
            InternalWellboreIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.rms,
                mapping_type=MappingType.wellbore,
                relation_type=InternalRelationType.primary,
                source_id=source_id,
                source_uuid=None,
                target_id=source_id,
                target_uuid=None,
            ),
            InternalWellboreIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.simulator,
                mapping_type=MappingType.wellbore,
                relation_type=InternalRelationType.primary,
                source_id=source_id,
                source_uuid=None,
                target_id=target_id,
                target_uuid=None,
            ),
        ]
    )


@pytest.fixture
def wellbore_mappings() -> InternalWellboreMappings:
    """Returns a valid InternalWellboreMappings object."""
    return _wellbore_mappings("30_9-B-43_A", "B43A")


@pytest.fixture
def stratigraphy_mappings() -> InternalStratigraphyMappings:
    """Returns a valid InternalStratigraphyMappings object."""
    return _stratigraphy_mappings(
        "TopVolantis",
        "VOLANTIS GP. Top",
        "TopVOLANTIS",
        "TOP_VOLANTIS",
    )


def test_mappings_manager_instantiation(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests basic facts about the Mappings resource Manager."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)

    assert mappings_manager.fmu_dir == fmu_dir
    assert mappings_manager.relative_path == Path("mappings.json")

    expected_path = mappings_manager.fmu_dir.path / mappings_manager.relative_path
    assert mappings_manager.path == expected_path
    assert mappings_manager.model_class == InternalMappings
    assert mappings_manager.exists is False

    with pytest.raises(
        FileNotFoundError, match="Resource file for 'MappingsManager' not found"
    ):
        mappings_manager.load()


def test_mappings_manager_update_internal_stratigraphy_mappings_overwrites_mappings(
    fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: InternalStratigraphyMappings,
) -> None:
    """Tests that updating stratigraphy mappings overwrites existing mappings."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    assert mappings_manager.exists is False

    mappings_manager.update_internal_stratigraphy_mappings(stratigraphy_mappings)
    assert mappings_manager.exists is True
    mappings = mappings_manager.load()
    expected_no_of_mappings = 4
    assert len(mappings.stratigraphy) == expected_no_of_mappings
    assert mappings.stratigraphy[0] == stratigraphy_mappings[0]

    new_mappings = _stratigraphy_mappings("TopViking", "VIKING GP. Top")

    mappings_manager.update_internal_stratigraphy_mappings(new_mappings)

    # Assert that existing mappings are overwritten
    mappings = mappings_manager.load()
    assert len(mappings.stratigraphy) == 2
    assert mappings.stratigraphy == new_mappings


def test_mappings_manager_update_internal_stratigraphy_mappings_writes_to_changelog(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that each update of the stratigraphy mappings, writes to the changelog.

    Checks that saving the same mappings again is not logged.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    new_mappings = _stratigraphy_mappings("TopViking", "VIKING GP. Top")
    mappings_manager.update_internal_stratigraphy_mappings(new_mappings)

    changelog: Log[ChangeInfo] = mappings_manager.fmu_dir._changelog.load()
    assert len(changelog) == 1
    assert changelog[0].change_type == ChangeType.update
    assert changelog[0].file == "mappings.json"
    assert changelog[0].key == "stratigraphy"
    assert changelog[0].change == "Updated field 'stratigraphy'."
    assert changelog[0].structured_diff is not None

    mappings_manager.update_internal_stratigraphy_mappings(new_mappings)
    mappings_manager.update_internal_stratigraphy_mappings(new_mappings)

    assert len(mappings_manager.fmu_dir._changelog.load()) == 1


def test_internal_stratigraphy_mappings_converts_to_stratigraphy_mappings(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Valid .fmu stratigraphy mappings are converted to fmu-datamodels mappings."""
    mappings = InternalStratigraphyMappings(
        root=[
            *_stratigraphy_mappings(
                "TopVolantis",
                "VOLANTIS GP. Top",
                "TopVOLANTIS",
                "TOP_VOLANTIS",
            ),
            InternalStratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.rms,
                relation_type=InternalRelationType.primary,
                source_id="Seabase",
                target_id="Seabase",
                target_uuid=None,
            ),
            InternalStratigraphyIdentifierMapping(
                source_system=DataSystem.rms,
                target_system=DataSystem.smda,
                relation_type=InternalRelationType.unmappable,
                source_id="Seabase",
                target_id=None,
                target_uuid=None,
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
        {
            "source_system": "rms",
            "target_system": "smda",
            "mapping_type": "stratigraphy",
            "relation_type": "alias",
            "source_id": "TOP_VOLANTIS",
            "target_id": "VOLANTIS GP. Top",
        },
    ]


def test_mappings_manager_update_internal_wellbore_mappings_overwrites_mappings(
    fmu_dir: ProjectFMUDirectory,
    wellbore_mappings: InternalWellboreMappings,
) -> None:
    """Tests that updating wellbore mappings overwrites existing mappings."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    assert mappings_manager.exists is False

    mappings_manager.update_internal_wellbore_mappings(wellbore_mappings)
    assert mappings_manager.exists is True
    mappings = mappings_manager.load()
    assert len(mappings.wellbore) == 2
    assert mappings.wellbore[0] == wellbore_mappings[0]
    assert isinstance(mappings_manager.wellbore_mappings, WellboreMappings)
    assert mappings_manager.wellbore_mappings.model_dump(
        mode="json", exclude_none=True
    ) == [
        {
            "source_system": "rms",
            "target_system": "simulator",
            "mapping_type": "wellbore",
            "relation_type": "primary",
            "source_id": "30_9-B-43_A",
            "target_id": "B43A",
        }
    ]

    new_mappings = _wellbore_mappings("30_9-B-43_B", "B43B")

    mappings_manager.update_internal_wellbore_mappings(new_mappings)

    # Assert that existing mappings are overwritten
    mappings = mappings_manager.load()
    assert len(mappings.wellbore) == 2
    assert mappings.wellbore == new_mappings


def test_mappings_manager_update_internal_wellbore_mappings_writes_to_changelog(
    fmu_dir: ProjectFMUDirectory,
    wellbore_mappings: InternalWellboreMappings,
) -> None:
    """Tests that each update of the wellbore mappings writes to the changelog.

    Checks that saving the same mappings again is not logged.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)

    mappings_manager.update_internal_wellbore_mappings(wellbore_mappings)

    changelog: Log[ChangeInfo] = mappings_manager.fmu_dir._changelog.load()
    assert len(changelog) == 1
    assert changelog[0].change_type == ChangeType.update
    assert changelog[0].file == "mappings.json"
    assert changelog[0].key == "wellbore"
    assert changelog[0].change == "Updated field 'wellbore'."
    assert changelog[0].structured_diff is not None

    mappings_manager.update_internal_wellbore_mappings(wellbore_mappings)
    mappings_manager.update_internal_wellbore_mappings(wellbore_mappings)

    assert len(mappings_manager.fmu_dir._changelog.load()) == 1


@pytest.mark.parametrize(
    ("changes", "expected_before", "expected_after"),
    [
        ({"target_id": "B44"}, {"target_id": "B43A"}, {"target_id": "B44"}),
        (
            {"source_uuid": UUID(int=1), "target_uuid": UUID(int=2)},
            {"source_uuid": None, "target_uuid": None},
            {"source_uuid": str(UUID(int=1)), "target_uuid": str(UUID(int=2))},
        ),
        (
            {"relation_type": InternalRelationType.unmappable, "target_id": None},
            {"relation_type": "primary", "target_id": "B43A"},
            {"relation_type": "unmappable", "target_id": None},
        ),
    ],
    ids=["target_id", "uuids", "unmappable"],
)
def test_mappings_manager_update_internal_wellbore_mappings_logs_changed_fields(
    fmu_dir: ProjectFMUDirectory,
    wellbore_mappings: InternalWellboreMappings,
    changes: dict[str, Any],
    expected_before: dict[str, Any],
    expected_after: dict[str, Any],
) -> None:
    """Tests that an edited wellbore mapping is logged with only its changed fields.

    Checks that the mapping keeps its identity key, so that it is logged as updated.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.update_internal_wellbore_mappings(wellbore_mappings)
    edited_mapping = wellbore_mappings[1].model_copy(update=changes)

    mappings_manager.update_internal_wellbore_mappings(
        InternalWellboreMappings(root=[wellbore_mappings[0], edited_mapping])
    )

    changelog: Log[ChangeInfo] = fmu_dir._changelog.load(force=True)
    assert changelog[-1].structured_diff == [
        ListFieldDiff(
            field_path="wellbore.root",
            added=[],
            removed=[],
            updated=[
                ListUpdatedEntry(
                    key=["wellbore", "rms", "simulator", "30_9-B-43_A"],
                    before=expected_before,
                    after=expected_after,
                )
            ],
        )
    ]


def test_mappings_manager_update_internal_wellbore_mappings_ignores_order(
    fmu_dir: ProjectFMUDirectory,
    wellbore_mappings: InternalWellboreMappings,
) -> None:
    """Tests that reordered wellbore mappings are not logged."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.update_internal_wellbore_mappings(wellbore_mappings)

    mappings_manager.update_internal_wellbore_mappings(
        InternalWellboreMappings(root=list(reversed(wellbore_mappings.root)))
    )

    changelog: Log[ChangeInfo] = fmu_dir._changelog.load()
    assert len(changelog) == 1


@pytest.mark.parametrize(
    ("mapping_type", "target_system"),
    [("wellbore", "simulator"), ("stratigraphy", "smda")],
)
def test_mappings_manager_failed_update_keeps_old_mappings(
    fmu_dir: ProjectFMUDirectory, mapping_type: str, target_system: str
) -> None:
    """Tests that a failed update keeps the old mappings and changelog.

    Checks that the next update is compared with the last saved mappings.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)

    def update_mappings(target_id: str) -> None:
        if mapping_type == "wellbore":
            mappings_manager.update_internal_wellbore_mappings(
                _wellbore_mappings("A", target_id)
            )
        else:
            mappings_manager.update_internal_stratigraphy_mappings(
                _stratigraphy_mappings("A", target_id)
            )

    update_mappings("B")
    old_mappings = mappings_manager.load()
    old_file_content = mappings_manager.path.read_text()

    with (
        patch.object(fmu_dir, "write_text_file", side_effect=PermissionError),
        pytest.raises(PermissionError),
    ):
        update_mappings("C")

    assert mappings_manager.path.read_text() == old_file_content
    assert mappings_manager.load() is old_mappings
    assert len(fmu_dir._changelog.load()) == 1

    update_mappings("C")

    changelog: Log[ChangeInfo] = fmu_dir._changelog.load(force=True)
    assert changelog[-1].structured_diff == [
        ListFieldDiff(
            field_path=f"{mapping_type}.root",
            added=[],
            removed=[],
            updated=[
                ListUpdatedEntry(
                    key=[mapping_type, "rms", target_system, "A"],
                    before={"target_id": "B"},
                    after={"target_id": "C"},
                )
            ],
        )
    ]


def test_mappings_manager_diff(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: InternalStratigraphyMappings,
) -> None:
    """Tests that the mappings diff equals the mappings from the incoming resource."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.update_internal_stratigraphy_mappings(stratigraphy_mappings)

    new_mappings_manager: MappingsManager = MappingsManager(extra_fmu_dir)
    new_mappings_manager.update_internal_stratigraphy_mappings(
        _stratigraphy_mappings("TopViking", "VIKING GP. Top")
    )

    diff = mappings_manager.get_mappings_diff(new_mappings_manager)

    assert len(diff.stratigraphy) == 2
    assert diff.stratigraphy == new_mappings_manager.load().stratigraphy


def test_mappings_manager_diff_mappings_raises(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: InternalStratigraphyMappings,
) -> None:
    """Exception is raised when any of the mappings resources to diff does not exist.

    When trying to diff two mapping resources, the mappings file must
    exist in both directories in order to make a diff.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    new_mappings_manager: MappingsManager = MappingsManager(extra_fmu_dir)

    expected_exp = (
        "Mappings resources to diff must exist in both directories: "
        "Current mappings resource exists: {}. "
        "Incoming mappings resource exists: {}."
    )

    with pytest.raises(FileNotFoundError, match=expected_exp.format("False", "False")):
        mappings_manager.get_mappings_diff(new_mappings_manager)

    mappings_manager.update_internal_stratigraphy_mappings(stratigraphy_mappings)

    with pytest.raises(FileNotFoundError, match=expected_exp.format("True", "False")):
        mappings_manager.get_mappings_diff(new_mappings_manager)

    with pytest.raises(FileNotFoundError, match=expected_exp.format("False", "True")):
        new_mappings_manager.get_mappings_diff(mappings_manager)

    new_mappings_manager.update_internal_stratigraphy_mappings(stratigraphy_mappings)
    assert mappings_manager.get_mappings_diff(new_mappings_manager)


def test_mappings_manager_merge_mappings(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: InternalStratigraphyMappings,
    wellbore_mappings: InternalWellboreMappings,
) -> None:
    """Tests that mappings from the incoming resource will overwrite current mappings.

    The current resource should be updated with all the mappings
    from the incoming resource.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.update_internal_stratigraphy_mappings(stratigraphy_mappings)
    assert mappings_manager.internal_stratigraphy_mappings == stratigraphy_mappings

    new_mappings_manager: MappingsManager = MappingsManager(extra_fmu_dir)
    new_mappings_manager.update_internal_stratigraphy_mappings(
        InternalStratigraphyMappings(root=[])
    )

    updated_mappings = mappings_manager.merge_mappings(new_mappings_manager)

    assert len(updated_mappings.stratigraphy) == 0
    assert (
        updated_mappings.stratigraphy == mappings_manager.internal_stratigraphy_mappings
    )
    assert len(updated_mappings.wellbore) == 0

    mappings_manager.update_internal_stratigraphy_mappings(stratigraphy_mappings)
    expected_no_of_mappings = 4
    assert (
        len(mappings_manager.internal_stratigraphy_mappings) == expected_no_of_mappings
    )

    new_mappings_manager.update_internal_stratigraphy_mappings(
        _stratigraphy_mappings("TopViking", "VIKING GP. Top")
    )
    assert len(new_mappings_manager.internal_stratigraphy_mappings) == 2

    updated_mappings = mappings_manager.merge_mappings(new_mappings_manager)

    assert len(updated_mappings.stratigraphy) == 2
    assert (
        updated_mappings.stratigraphy == mappings_manager.internal_stratigraphy_mappings
    )
    assert (
        mappings_manager.internal_stratigraphy_mappings
        == new_mappings_manager.internal_stratigraphy_mappings
    )

    new_mappings_manager.update_internal_wellbore_mappings(wellbore_mappings)
    updated_mappings = mappings_manager.merge_mappings(new_mappings_manager)
    assert updated_mappings.wellbore == mappings_manager.internal_wellbore_mappings
    assert (
        mappings_manager.internal_wellbore_mappings
        == new_mappings_manager.internal_wellbore_mappings
    )
    assert len(updated_mappings.wellbore) == 2


def test_mappings_manager_merge_changes(
    fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: InternalStratigraphyMappings,
    wellbore_mappings: InternalWellboreMappings,
) -> None:
    """Tests that mappings from the change object will overwrite current mappings.

    The current resource should be updated with all the mappings
    from the change object.
    """
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.update_internal_stratigraphy_mappings(stratigraphy_mappings)
    assert mappings_manager.internal_stratigraphy_mappings == stratigraphy_mappings

    # Assert empty change object overwrites current mappings
    change_object = InternalMappings()
    updated_mappings = mappings_manager.merge_changes(change_object)
    assert (
        updated_mappings.stratigraphy == mappings_manager.internal_stratigraphy_mappings
    )
    assert len(mappings_manager.internal_stratigraphy_mappings) == 0
    assert len(mappings_manager.internal_wellbore_mappings) == 0

    new_mappings = _stratigraphy_mappings("TopViking", "VIKING GP. Top")

    # Assert change object overwrites current mappings
    change_object.stratigraphy = new_mappings
    updated_mappings = mappings_manager.merge_changes(change_object)

    assert len(updated_mappings.wellbore) == 0
    assert len(updated_mappings.stratigraphy) == 2
    assert updated_mappings.stratigraphy == new_mappings
    assert mappings_manager.internal_stratigraphy_mappings == new_mappings

    change_object.wellbore = wellbore_mappings
    updated_mappings = mappings_manager.merge_changes(change_object)
    assert updated_mappings.wellbore == wellbore_mappings
    assert mappings_manager.internal_wellbore_mappings == wellbore_mappings
    assert len(updated_mappings.wellbore) == 2


def test_mappings_manager_update_internal_stratigraphy_mappings_logs_changed_fields(
    fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: InternalStratigraphyMappings,
) -> None:
    """Tests that an edited stratigraphy mapping is logged with its changed fields."""
    mappings_manager: MappingsManager = MappingsManager(fmu_dir)
    mappings_manager.update_internal_stratigraphy_mappings(stratigraphy_mappings)
    edited_mapping = stratigraphy_mappings[3].model_copy(
        update={"target_id": "VIKING GP. Top"}
    )

    mappings_manager.update_internal_stratigraphy_mappings(
        InternalStratigraphyMappings(
            root=[*stratigraphy_mappings.root[:3], edited_mapping]
        )
    )

    changelog: Log[ChangeInfo] = fmu_dir._changelog.load(force=True)
    assert changelog[-1].structured_diff == [
        ListFieldDiff(
            field_path="stratigraphy.root",
            added=[],
            removed=[],
            updated=[
                ListUpdatedEntry(
                    key=["stratigraphy", "rms", "smda", "TopVolantis"],
                    before={"target_id": "VOLANTIS GP. Top"},
                    after={"target_id": "VIKING GP. Top"},
                )
            ],
        )
    ]


def test_mappings_manager_structured_diff_detects_added_removed_items(
    fmu_dir: ProjectFMUDirectory,
    stratigraphy_mappings: InternalStratigraphyMappings,
) -> None:
    """Tests that mappings with a new source identity are added and removed."""
    mappings_manager = MappingsManager(fmu_dir)

    replacement_mappings = _stratigraphy_mappings("TopViking", "VIKING GP. Top")

    current_model = InternalMappings(stratigraphy=stratigraphy_mappings)
    incoming_model = InternalMappings(
        stratigraphy=InternalStratigraphyMappings(
            root=[
                stratigraphy_mappings[0],
                stratigraphy_mappings[2],
                stratigraphy_mappings[3],
                *replacement_mappings,
            ]
        )
    )

    model_diff = mappings_manager.get_structured_model_diff(
        current_model, incoming_model
    )

    assert len(model_diff) == 1
    diff = model_diff[0]
    assert isinstance(diff, ListFieldDiff)
    assert diff.field_path == "stratigraphy.root"
    assert len(diff.added) == 2
    assert len(diff.removed) == 1
    assert diff.updated == []
    assert {mapping["source_id"] for mapping in diff.added} == {"TopViking"}
    assert diff.removed[0]["source_id"] == "TopVOLANTIS"


def test_build_global_config_stratigraphy_empty(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Empty stratigraphy when no mappings and no RMS config."""
    mappings_manager = MappingsManager(fmu_dir)
    strat = mappings_manager.build_global_config_stratigraphy()
    assert strat.model_dump() == {}


def test_build_global_config_stratigraphy_only_rms(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """All entries are non-stratigraphic when there are no mappings."""
    fmu_dir.update_config(
        {
            "rms": {
                "path": "rms/model/test.rms15.0.1.0",
                "version": "15.0.1.0",
                "horizons": [
                    {"name": "MSL", "type": "interpreted"},
                    {"name": "TopX", "type": "interpreted"},
                ],
                "zones": [
                    {
                        "name": "Above",
                        "top_horizon_name": "MSL",
                        "base_horizon_name": "TopX",
                    }
                ],
            }
        }
    )

    mappings_manager = MappingsManager(fmu_dir)
    strat = mappings_manager.build_global_config_stratigraphy()

    result = strat.model_dump(mode="json", exclude_none=True, exclude_unset=True)
    for name in ("MSL", "TopX", "Above"):
        assert result[name] == {"stratigraphic": False, "name": name}
    assert len(result) == 3  # noqa: PLR2004


def test_build_global_config_stratigraphy_handles_optional_rms_lists(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Missing RMS horizons and zones should be treated as empty lists."""
    fmu_dir.update_config(
        {
            "rms": {
                "path": "rms/model/test.rms15.0.1.0",
                "version": "15.0.1.0",
            }
        }
    )

    mappings_manager = MappingsManager(fmu_dir)
    strat = mappings_manager.build_global_config_stratigraphy()

    assert strat.model_dump() == {}


def test_build_global_config_stratigraphy_only_mappings(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Only stratigraphic entries when there is no RMS config."""
    mappings_manager = MappingsManager(fmu_dir)
    target_uuid = UUID("00000000-0000-0000-0000-000000000001")
    mappings_manager.update_internal_stratigraphy_mappings(
        _stratigraphy_mappings("TopX", "X Fm. Top", target_uuid=target_uuid)
    )

    strat = mappings_manager.build_global_config_stratigraphy()

    result = strat.model_dump(mode="json", exclude_none=True, exclude_unset=True)
    assert result == {
        "TopX": {
            "stratigraphic": True,
            "name": "X Fm. Top",
            "uuid": str(target_uuid),
        }
    }


def test_build_global_config_stratigraphy_mapped_horizon_not_duplicated(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A horizon with a primary mapping appears once as stratigraphic, not twice."""
    fmu_dir.update_config(
        {
            "rms": {
                "path": "rms/model/test.rms15.0.1.0",
                "version": "15.0.1.0",
                "horizons": [
                    {"name": "TopX", "type": "interpreted"},
                    {"name": "MSL", "type": "interpreted"},
                ],
                "zones": [],
            }
        }
    )
    mappings_manager = MappingsManager(fmu_dir)
    mappings_manager.update_internal_stratigraphy_mappings(
        _stratigraphy_mappings("TopX", "X Fm. Top")
    )

    strat = mappings_manager.build_global_config_stratigraphy()

    result = strat.model_dump(mode="json", exclude_none=True, exclude_unset=True)
    assert result["TopX"] == {"stratigraphic": True, "name": "X Fm. Top"}
    assert result["MSL"] == {"stratigraphic": False, "name": "MSL"}
    assert len(result) == 2  # noqa: PLR2004


def test_build_global_config_stratigraphy_correct_drogon_integration(
    drogon_fmu_dir: ProjectFMUDirectory,
) -> None:
    """Drogon global config stratigraphy reconstructed from mappings and RMS."""
    stratigraphy = drogon_fmu_dir._mappings.build_global_config_stratigraphy()
    assert (
        stratigraphy.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        == GLOBAL_CONFIG_STRATIGRAPHY
    )
