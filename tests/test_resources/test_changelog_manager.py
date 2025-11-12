"""Tests for ChangelogManager."""

import copy
import uuid
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fmu.datamodels.fmu_results.fields import StratigraphicColumn

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.changelog_manager import ChangelogManager
from fmu.settings.models._enums import ChangeType, FilterType
from fmu.settings.models.change_info import ChangeInfo
from fmu.settings.models.log import Filter, Log, LogFileName

DATE_TIME_NOW = datetime.now(UTC)


@pytest.fixture
def change_entry() -> ChangeInfo:
    """Returns a valid ChangeInfo object."""
    return ChangeInfo(
        timestamp=DATE_TIME_NOW,
        change_type=ChangeType.add,
        user="test",
        path=Path("/test_folder"),
        file="config.json",
        change="Added new field to smda masterdata.",
        hostname="hostname",
        key="masterdata",
    )


@pytest.fixture
def change_entry_list() -> list[ChangeInfo]:
    """Returns a list of valid ChangeInfo entries."""
    return [
        ChangeInfo(
            timestamp=DATE_TIME_NOW - timedelta(days=2),
            change_type=ChangeType.add,
            user="user_first_entry",
            path=Path("/path_first_entry"),
            file="config.json",
            change="Added new field.",
            hostname="hostname_first_entry",
            key="masterdata",
        ),
        ChangeInfo(
            timestamp=DATE_TIME_NOW - timedelta(days=1),
            change_type=ChangeType.update,
            user="user_second_entry",
            path=Path("/path_second_entry"),
            file="config.json",
            change="Updated field.",
            hostname="hostname_second_entry",
            key="masterdata",
        ),
        ChangeInfo(
            timestamp=DATE_TIME_NOW,
            change_type=ChangeType.remove,
            user="user_third_entry",
            path=Path("/path_third_entry"),
            file="config.json",
            change="Removed field.",
            hostname="hostname_third_entry",
            key="masterdata",
        ),
        ChangeInfo(
            timestamp=DATE_TIME_NOW,
            change_type=ChangeType.reset,
            user="user_fourth_entry",
            path=Path("/path_fourth_entry"),
            file="config.json",
            change="Reset field.",
            hostname="hostname_fourth_entry",
            key="masterdata",
        ),
    ]


def test_changelog_manager_instantiation(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests basic facts about the ChangelogManager."""
    changelog: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog.fmu_dir == fmu_dir
    assert changelog.relative_path == Path("logs") / LogFileName.changelog
    assert changelog.exists is False
    with pytest.raises(
        FileNotFoundError, match="Resource file for 'ChangelogManager' not found"
    ):
        changelog.load()

    assert changelog.model_class == Log[ChangeInfo]


def test_changelog_manager_add_entry(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests adding a new entry to a non-existing changelog.

    This should create the changelog file and add the new entry at the end.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog_resource.exists is False
    with pytest.raises(
        FileNotFoundError, match="Resource file for 'ChangelogManager' not found"
    ):
        changelog_resource.load()

    changelog_resource.add_log_entry(change_entry)

    assert changelog_resource.exists is True
    changelog = changelog_resource.load()
    assert changelog[0] == change_entry

    changelog_resource.add_log_entry(change_entry)
    changelog_resource.add_log_entry(change_entry)
    expected_log_entries = 3

    updated_changelog: Log[ChangeInfo] = changelog_resource.load()
    assert len(updated_changelog) == expected_log_entries


def test_changelog_manager_add_invalid_entry(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests adding an invalid entry to an existing changelog.

    This should raise a Value error and not add the invalid log entry.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    changelog_resource.add_log_entry(change_entry)
    assert changelog_resource.exists

    change_entry_with_issues = copy.deepcopy(change_entry)
    del change_entry_with_issues.change_type

    with pytest.raises(
        ValueError, match=r"Invalid log entry added to 'Log\[ChangeInfo\]' "
    ):
        changelog_resource.add_log_entry(change_entry_with_issues)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    assert len(changelog) == 1
    assert changelog[0] == change_entry


def test_changelog_manager_add_invalid_entry_no_file_created(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests adding an invalid entry to a non-existing changelog.

    This should raise a Value error and not create the changelog file.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog_resource.exists is False

    change_entry_with_issues = copy.deepcopy(change_entry)
    change_entry_with_issues.change_type = "invalid change_type"  # type: ignore

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        with pytest.raises(
            ValueError, match=r"Invalid log entry added to 'Log\[ChangeInfo\]' "
        ):
            changelog_resource.add_log_entry(change_entry_with_issues)

    assert changelog_resource.exists is False


def test_changelog_filter_equal_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with == operator.

    The filter should return all changelog entries where the value of the field
    `field_name` equals the filter value.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 4
    assert len(changelog) == expected_log_entries

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type=FilterType.text,
        operator="==",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 1
    assert filtered_log[0] == changelog[0]

    filter = Filter(
        field_name="user",
        filter_value="user_second_entry",
        filter_type=FilterType.text,
        operator="==",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 1
    assert filtered_log[0] == changelog[1]

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW),
        filter_type=FilterType.date,
        operator="==",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 2
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp == DATE_TIME_NOW for entry in filtered_log)

    filter = Filter(
        field_name="change",
        filter_value="Changed field.",
        filter_type=FilterType.text,
        operator="==",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_filter_not_equal_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with != operator.

    The filter should return all changelog entries where the value of the field
    `field_name` is not equal to the filter value.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 4
    assert len(changelog) == expected_log_entries

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type=FilterType.text,
        operator="!=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 3
    assert len(filtered_log) == expected_log_entries
    assert all(entry.change_type is not ChangeType.add for entry in filtered_log)

    filter = Filter(
        field_name="user",
        filter_value="user_second_entry",
        filter_type=FilterType.text,
        operator="!=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 3
    assert len(filtered_log) == expected_log_entries
    assert all(entry.user != "user_second_entry" for entry in filtered_log)

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW),
        filter_type=FilterType.date,
        operator="!=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 2
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp != DATE_TIME_NOW for entry in filtered_log)

    filter = Filter(
        field_name="key",
        filter_value="masterdata",
        filter_type=FilterType.text,
        operator="!=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_filter_less_or_equal_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with <= operator.

    The filter should return all changelog entries where the value of the field
    `field_name` is less or equal to the filter value. Attempts to filter
    strings with the <= operator should raise an exception.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 4
    assert len(changelog) == expected_log_entries

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type=FilterType.text,
        operator="<=",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator <= applied to 'text' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    filter = Filter(
        field_name="user",
        filter_value="user_third_entry",
        filter_type=FilterType.text,
        operator="<=",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator <= applied to 'text' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    yesterday = DATE_TIME_NOW - timedelta(days=1)
    filter = Filter(
        field_name="timestamp",
        filter_value=str(yesterday),
        filter_type=FilterType.date,
        operator="<=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 2
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp <= yesterday for entry in filtered_log)

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW - timedelta(days=3)),
        filter_type=FilterType.date,
        operator="<=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_filter_greater_or_equal_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with >= operator.

    The filter should return all changelog entries where the value of the field
    `field_name` is greater or equal to the filter value. Attempts to filter
    strings with the >= operator should raise an exception.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 4
    assert len(changelog) == expected_log_entries

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type=FilterType.text,
        operator=">=",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator >= applied to 'text' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    filter = Filter(
        field_name="user",
        filter_value="user_third_entry",
        filter_type=FilterType.text,
        operator=">=",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator >= applied to 'text' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    yesterday = DATE_TIME_NOW - timedelta(days=1)
    filter = Filter(
        field_name="timestamp",
        filter_value=str(yesterday),
        filter_type=FilterType.date,
        operator=">=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 3
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp >= yesterday for entry in filtered_log)

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW + timedelta(days=1)),
        filter_type=FilterType.date,
        operator=">=",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_dataframe_cached_after_filtering(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests that _cached_dataframe is set after filtering has been applied."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog_resource._cached_dataframe is None
    changelog_resource.add_log_entry(change_entry)
    assert changelog_resource._cached_dataframe is None

    filter: Filter = Filter(
        field_name="change_type",
        filter_value=ChangeType.add,
        filter_type=FilterType.text,
        operator="==",
    )
    changelog_resource.filter_log(filter)
    assert changelog_resource._cached_dataframe is not None


def test_changelog_dataframe_cache_cleared(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests that _cached_dataframe is cleared when the changelog is updated."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    assert changelog_resource._cached_dataframe is None

    changelog_resource._cached_dataframe = pd.DataFrame(["some_data"])
    assert changelog_resource._cached_dataframe is not None

    changelog_resource.add_log_entry(change_entry)
    assert changelog_resource._cached_dataframe is None


def test_log_update_to_changelog_when_flat_dict(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that updates of flat dictionaries are logged as expected.

    Checks that the key, change_type and change fields are logged with correct values.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)

    first_key = "first_key"
    first_value = "first_test_value"
    old_resource_dict = {first_key: first_value, "some_key": "some_value"}

    updated_value = "updated_value"
    added_key = "added_key"
    added_value = "added_value"
    updates: dict[str, Any] = {
        first_key: updated_value,
        added_key: added_value,
    }

    changelog_resource.log_update_to_changelog(
        updates, old_resource_dict, Path("config.json")
    )

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 2
    assert len(changelog) == expected_log_entries

    expected_change_string = (
        f"Updated field '{first_key}'. Old value: {first_value}"
        f" -> New value: {updated_value}"
    )
    assert changelog[0].change_type == ChangeType.update
    assert changelog[0].change == expected_change_string

    expected_change_string = f"Added field '{added_key}'. New value: {added_value}"
    assert changelog[1].change_type == ChangeType.add
    assert expected_change_string == changelog[1].change


def test_log_update_to_changelog_when_nested_dict(
    fmu_dir: ProjectFMUDirectory, masterdata_dict: dict[str, Any]
) -> None:
    """Tests that updates of nested dictionaries are logged as expected.

    Checks that the key, change_type and change fields are logged with correct values.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)

    updated_country = [
        {
            "identifier": "Norge",
            "uuid": "00000000-0000-0000-0000-000000000000",
        }
    ]

    first_key = "smda.country"
    new_key = "new_key"
    new_nested_key = "new.nested.key"
    updates: dict[str, Any] = {
        first_key: updated_country,
        new_key: "new_value",
        new_nested_key: "new_nested_value",
    }

    changelog_resource.log_update_to_changelog(
        updates, masterdata_dict, Path("config.json")
    )

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 3
    assert len(changelog) == expected_log_entries

    expected_old_value = str(masterdata_dict["smda"]["country"])
    expected_change_string = (
        f"Updated field '{first_key}'. Old value: {expected_old_value}"
        f" -> New value: {str(updated_country)}"
    )

    assert changelog[0].change_type == ChangeType.update
    assert changelog[0].change == expected_change_string

    expected_change_string = f"Added field '{new_key}'. New value: new_value"
    assert changelog[1].change_type == ChangeType.add
    assert expected_change_string == changelog[1].change

    expected_change_string = (
        f"Added field '{new_nested_key}'. New value: new_nested_value"
    )
    assert changelog[2].change_type == ChangeType.add
    assert expected_change_string == changelog[2].change


def test_log_update_to_changelog_when_none_values(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that updates with None values are logged as expected.

    Checks that the key, change_type and change fields are logged with correct values.
    """
    first_key = "first_key"
    first_value = "first_test_value"
    second_key = "some_key"
    old_resource_dict = {first_key: first_value, second_key: None}

    updated_value = "updated_value"
    added_key = "added_key"
    updates: dict[str, Any] = {
        first_key: None,
        second_key: updated_value,
        added_key: None,
    }

    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    changelog_resource.log_update_to_changelog(
        updates, old_resource_dict, Path("config.json")
    )

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 3
    assert len(changelog) == expected_log_entries

    assert changelog[0].change_type == ChangeType.update
    expected_change_string = (
        f"Updated field '{first_key}'. Old value: {first_value}"
        f" -> New value: {str(None)}"
    )
    assert changelog[0].change == expected_change_string

    assert changelog[1].change_type == ChangeType.update
    expected_change_string = (
        f"Updated field '{second_key}'. Old value: {str(None)}"
        f" -> New value: {updated_value}"
    )
    assert changelog[1].change == expected_change_string

    assert changelog[2].change_type == ChangeType.add
    expected_change_string = f"Added field '{added_key}'. New value: {str(None)}"
    assert changelog[2].change_type == ChangeType.add
    assert expected_change_string == changelog[2].change


def test_log_update_to_changelog_when_base_model_values(
    fmu_dir: ProjectFMUDirectory, masterdata_dict: dict[str, Any]
) -> None:
    """Tests that updates to BaseModel objects are logged as expected.

    Checks that the key, change_type and change fields are logged with correct values.
    """
    strat_column = StratigraphicColumn(identifier="test_strat", uuid=uuid.uuid4())

    test_update = "smda.stratigraphic_column"
    test_add = "new.field"
    updates: dict[str, Any] = {test_update: strat_column, test_add: strat_column}

    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    changelog_resource.log_update_to_changelog(
        updates, masterdata_dict, Path("config.json")
    )

    changelog: Log[ChangeInfo] = changelog_resource.load()
    expected_log_entries = 2
    assert len(changelog) == expected_log_entries

    assert changelog[0].key == test_update
    assert changelog[0].change_type == ChangeType.update
    old_value = masterdata_dict["smda"]["stratigraphic_column"]
    expected_change_string = (
        f"Updated field '{test_update}'. Old value: {str(old_value)}"
        f" -> New value: {str(strat_column.model_dump())}"
    )
    assert expected_change_string == changelog[0].change

    assert changelog[1].key == test_add
    assert changelog[1].change_type == ChangeType.add
    expected_change_string = (
        f"Added field '{test_add}'. New value: {str(strat_column.model_dump())}"
    )
    assert expected_change_string == changelog[1].change
