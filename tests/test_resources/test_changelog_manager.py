"""Tests for ChangelogManager."""

import copy
import json
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.changelog_manager import ChangelogManager
from fmu.settings.models._enums import ChangeType, FilterType
from fmu.settings.models.change_info import ChangeInfo
from fmu.settings.models.diff import ResourceDiff, ScalarFieldDiff
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


def test_changelog_manager_log_init_to_changelog(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that init logging writes the expected changelog entry."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)

    changelog_resource.log_init_to_changelog()

    changelog = changelog_resource.load()
    assert len(changelog) == 1

    init_entry = changelog[0]
    assert init_entry.change_type == ChangeType.init
    assert init_entry.path == fmu_dir.path
    assert init_entry.file == "N/A"
    assert init_entry.key == "project_initialization"
    assert init_entry.change == f"Initialized .fmu directory at '{fmu_dir.path}'."


def test_changelog_manager_log_restore_to_changelog(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that restore logging writes the expected changelog entry."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    relative_path = Path("mappings.json")
    source = "cache revision '20260619090000'"

    changelog_resource.log_restore_to_changelog(
        relative_path=relative_path, source=source
    )

    changelog = changelog_resource.load()
    assert len(changelog) == 1

    restore_entry = changelog[0]
    assert restore_entry.change_type == ChangeType.restore
    assert restore_entry.path == fmu_dir.path
    assert restore_entry.file == str(relative_path)
    assert restore_entry.key == "mappings"
    assert restore_entry.change == f"Restored '{relative_path}' from {source}."


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


def test_changelog_filter_greater_than_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with > operator.

    The filter should return all changelog entries where the value of the field
    `field_name` is greater than the filter value. Attempts to filter
    strings with the > operator should raise an exception.
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
        operator=">",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator > applied to 'text' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    filter = Filter(
        field_name="user",
        filter_value="user_third_entry",
        filter_type=FilterType.text,
        operator=">",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator > applied to 'text' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    yesterday = DATE_TIME_NOW - timedelta(days=1)
    filter = Filter(
        field_name="timestamp",
        filter_value=str(yesterday),
        filter_type=FilterType.date,
        operator=">",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 2
    assert len(filtered_log) == expected_log_entries
    assert all(entry.timestamp > yesterday for entry in filtered_log)

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW),
        filter_type=FilterType.date,
        operator=">",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 0


def test_changelog_filter_less_than_operator(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests filtering changelog with < operator.

    The filter should return all changelog entries where the value of the field
    `field_name` is less than the filter value. Attempts to filter
    strings with the < operator should raise an exception.
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
        operator="<",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator < applied to 'text' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    filter = Filter(
        field_name="user",
        filter_value="user_third_entry",
        filter_type=FilterType.text,
        operator="<",
    )
    with pytest.raises(
        ValueError, match="Invalid filter operator < applied to 'text' field"
    ):
        filtered_log = changelog_resource.filter_log(filter)

    yesterday = DATE_TIME_NOW - timedelta(days=1)
    filter = Filter(
        field_name="timestamp",
        filter_value=str(yesterday),
        filter_type=FilterType.date,
        operator="<",
    )
    filtered_log = changelog_resource.filter_log(filter)
    assert len(filtered_log) == 1

    filter = Filter(
        field_name="timestamp",
        filter_value=str(DATE_TIME_NOW + timedelta(days=1)),
        filter_type=FilterType.date,
        operator="<",
    )
    filtered_log = changelog_resource.filter_log(filter)
    expected_log_entries = 4
    assert len(filtered_log) == expected_log_entries


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


def test_log_update_to_changelog_writes_update_entry(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that an update key with a diff is logged as an update entry."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    diff = ScalarFieldDiff(field_path="model.name", before="old", after="new")

    changelog_resource.log_update_to_changelog(
        {"model.name": "new"}, Path("config.json"), structured_diff=[diff]
    )

    changelog: Log[ChangeInfo] = changelog_resource.load()
    assert len(changelog) == 1
    assert changelog[0].change_type == ChangeType.update
    assert changelog[0].change == "Updated field 'model.name'."
    assert changelog[0].key == "model.name"
    assert changelog[0].file == "config.json"
    assert changelog[0].path == fmu_dir.path
    assert changelog[0].structured_diff == [diff]


@pytest.mark.parametrize(
    ("update_keys", "diff_paths", "expected_entries"),
    [
        (
            ["model"],
            ["model.name", "model.description"],
            {"model": ["model.name", "model.description"]},
        ),
        (
            ["model", "model.name"],
            ["model.name", "model.description"],
            {"model": ["model.description"], "model.name": ["model.name"]},
        ),
        (
            ["rms.path", "rms.version"],
            ["rms"],
            {"rms": ["rms"]},
        ),
        (
            ["model.name"],
            ["model.description"],
            {"model.description": ["model.description"]},
        ),
        (
            ["model.name", "model.revision"],
            ["model.name"],
            {"model.name": ["model.name"]},
        ),
    ],
    ids=[
        "diffs_inside_key",
        "key_and_its_parent",
        "whole_parent_changed",
        "diff_outside_keys",
        "key_without_diffs",
    ],
)
def test_log_update_to_changelog_with_structured_diff(
    fmu_dir: ProjectFMUDirectory,
    update_keys: list[str],
    diff_paths: list[str],
    expected_entries: dict[str, list[str]],
) -> None:
    """Tests that each diff is logged once, in the entry of the key it belongs to.

    The expected entries show each diff by its field path.
    """
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    diffs: list[ResourceDiff] = [
        ScalarFieldDiff(field_path=path, before="old", after="new")
        for path in diff_paths
    ]

    changelog_resource.log_update_to_changelog(
        dict.fromkeys(update_keys),
        Path("config.json"),
        structured_diff=diffs,
    )

    changelog: Log[ChangeInfo] = changelog_resource.load()
    logged_entries = {
        entry.key: [diff.field_path for diff in entry.structured_diff or []]
        for entry in changelog
    }
    assert logged_entries == expected_entries


def test_changelog_loads_entries_without_structured_diff(
    fmu_dir: ProjectFMUDirectory, change_entry: ChangeInfo
) -> None:
    """Tests that entries written before structured diffs load without a diff."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    old_entry = change_entry.model_dump(mode="json", exclude={"structured_diff"})
    fmu_dir.write_text_file(changelog_resource.relative_path, json.dumps([old_entry]))

    changelog: Log[ChangeInfo] = changelog_resource.load()

    assert len(changelog) == 1
    assert changelog[0].change == change_entry.change
    assert changelog[0].structured_diff is None


def test_changelog_get_latest_change_timestamp(
    fmu_dir: ProjectFMUDirectory, change_entry_list: list[ChangeInfo]
) -> None:
    """Tests that the timestamp of the latest added log entry is returned."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    for change_entry in change_entry_list:
        changelog_resource.add_log_entry(change_entry)

    expected_latest_timestamp = change_entry_list[-1].timestamp
    assert (
        changelog_resource._get_latest_change_timestamp() == expected_latest_timestamp
    )


def test_changelog_get_changelog_diff_with_other_changelog(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    change_entry_list: list[ChangeInfo],
) -> None:
    """Tests that the new entries from the incoming changelog are returned.

    When getting a diff between two changelogs, all change entries in the incoming
    changelog newer than the log entries in the current changelog, should be returned.
    """
    current_changelog: ChangelogManager = ChangelogManager(fmu_dir)
    current_changelog.add_log_entry(
        ChangeInfo(
            timestamp=DATE_TIME_NOW - timedelta(days=1),
            change_type=ChangeType.add,
            user="old_test",
            path=Path("/test_folder"),
            file="config.json",
            change="Added new field to smda masterdata one day ago",
            hostname="hostname",
            key="masterdata",
        ),
    )
    incoming_changelog: ChangelogManager = ChangelogManager(extra_fmu_dir)
    for entry in change_entry_list:
        incoming_changelog.add_log_entry(entry)

    diff = current_changelog.get_changelog_diff(incoming_changelog)

    expected_diff_entries = 2
    assert len(diff) == expected_diff_entries
    assert diff[0] == change_entry_list[2]
    assert diff[1] == change_entry_list[3]

    starting_point = current_changelog._get_latest_change_timestamp()
    for entry in diff:
        assert entry.timestamp > starting_point
    assert change_entry_list[0].timestamp <= starting_point
    assert change_entry_list[1].timestamp <= starting_point


def test_changelog_get_changelog_diff_with_old_changelog(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    change_entry: ChangeInfo,
) -> None:
    """Tests that the diff is empty when all incoming changes are old.

    When the latest change in the current changelog is newer than the entries
    in the incoming changelog, the result should be an empty Log object.
    """
    current_changelog: ChangelogManager = ChangelogManager(fmu_dir)
    current_changelog.add_log_entry(change_entry)

    incoming_changelog: ChangelogManager = ChangelogManager(extra_fmu_dir)
    incoming_changelog.add_log_entry(
        ChangeInfo(
            timestamp=DATE_TIME_NOW - timedelta(seconds=2),
            change_type=ChangeType.add,
            user="old_test",
            path=Path("/test_folder"),
            file="config.json",
            change="Added new field to smda masterdata two seconds ago",
            hostname="hostname",
            key="masterdata",
        ),
    )
    incoming_changelog.add_log_entry(
        ChangeInfo(
            timestamp=DATE_TIME_NOW - timedelta(seconds=3),
            change_type=ChangeType.add,
            user="older_test",
            path=Path("/test_folder"),
            file="config.json",
            change="Added new field to smda masterdata three seconds ago.",
            hostname="hostname",
            key="masterdata",
        )
    )

    diff = current_changelog.get_changelog_diff(incoming_changelog)
    assert len(diff) == 0


def test_changelog_get_changelog_diff_with_other_changelog_raises(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    change_entry: ChangeInfo,
) -> None:
    """Exception is raised when any of the changelog resources to diff does not exist.

    When trying to diff two changelog resources, the changelog file must
    exist in both directories in order to make a diff.
    """
    current_changelog: ChangelogManager = ChangelogManager(fmu_dir)
    incoming_changelog: ChangelogManager = ChangelogManager(extra_fmu_dir)

    expected_exc_msg = (
        "Changelog resources to diff must exist in both directories: "
        "Current changelog resource exists: {}. "
        "Incoming changelog resource exists: {}."
    )
    with pytest.raises(
        FileNotFoundError, match=expected_exc_msg.format("False", "False")
    ):
        current_changelog.get_changelog_diff(incoming_changelog)

    current_changelog.add_log_entry(change_entry)
    with pytest.raises(
        FileNotFoundError, match=expected_exc_msg.format("True", "False")
    ):
        current_changelog.get_changelog_diff(incoming_changelog)

    with pytest.raises(
        FileNotFoundError, match=expected_exc_msg.format("False", "True")
    ):
        incoming_changelog.get_changelog_diff(current_changelog)


def test_changelog_merge_changelog_with_other_changelog(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    change_entry_list: list[ChangeInfo],
) -> None:
    """Tests merging a changelog resource with an incoming changelog.

    When merging two changelogs, all log entries from the incoming changelog newer
    than the log entries in the current changelog are added.
    """
    current_changelog: ChangelogManager = ChangelogManager(fmu_dir)
    existing_entry = ChangeInfo(
        timestamp=DATE_TIME_NOW - timedelta(days=1),
        change_type=ChangeType.add,
        user="old_test",
        path=Path("/test_folder"),
        file="config.json",
        change="Added new field to smda masterdata one day ago",
        hostname="hostname",
        key="masterdata",
    )
    current_changelog.add_log_entry(existing_entry)

    incoming_changelog: ChangelogManager = ChangelogManager(extra_fmu_dir)
    for entry in change_entry_list:
        incoming_changelog.add_log_entry(entry)

    updated_changelog = current_changelog.merge_changelog(incoming_changelog)

    expected_entries = 3
    assert len(updated_changelog) == expected_entries
    assert updated_changelog[0] == existing_entry
    assert updated_changelog[1] == change_entry_list[2]
    assert updated_changelog[2] == change_entry_list[3]

    current_log = current_changelog.load(force=True)
    assert updated_changelog == current_log


def test_changelog_merge_changes_into_current_changelog(
    fmu_dir: ProjectFMUDirectory,
    extra_fmu_dir: ProjectFMUDirectory,
    change_entry: ChangeInfo,
    change_entry_list: list[ChangeInfo],
) -> None:
    """Tests that all log entries in the change object are added to the changelog."""
    current_changelog: ChangelogManager = ChangelogManager(fmu_dir)
    current_changelog.add_log_entry(change_entry)

    new_changelog: ChangelogManager = ChangelogManager(extra_fmu_dir)
    for entry in change_entry_list:
        new_changelog.add_log_entry(entry)
    change = change_entry_list
    updated_changelog = current_changelog.merge_changes(change)

    expected_entries = 5
    assert len(updated_changelog) == expected_entries
    assert updated_changelog == current_changelog.load()


def test_changelog_log_merge_to_changelog_merge_details(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that the merge details logged to the changelog is as expected."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    source_path = changelog_resource.path.parent.parent
    incoming_path = Path("/some_path/.fmu")
    resources = ["config", "_changelog"]

    changelog_resource.log_merge_to_changelog(
        source_path=source_path, incoming_path=incoming_path, merged_resources=resources
    )

    changelog = changelog_resource.load()
    assert len(changelog) == 1
    merge_entry = changelog[0]
    assert merge_entry.change_type == ChangeType.merge
    assert merge_entry.path == source_path
    assert merge_entry.key == ".fmu"

    expected_change_string = (
        f"Merged resources 'config', '_changelog' from "
        f"'{incoming_path}' into '{source_path}'."
    )
    assert merge_entry.change == expected_change_string


def test_changelog_log_copy_revision_to_changelog(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that the revision copy details logged to the changelog is as expected."""
    changelog_resource: ChangelogManager = ChangelogManager(fmu_dir)
    source_path = Path("path/to/master/project/revision")

    changelog_resource.log_copy_revision_to_changelog(source_path=source_path)

    changelog = changelog_resource.load()
    assert len(changelog) == 1
    copy_entry = changelog[0]
    assert copy_entry.change_type == ChangeType.copy
    assert copy_entry.path == source_path
    assert copy_entry.change == f"Copied project revision from {source_path}."
    assert copy_entry.file == "N/A"
    assert copy_entry.key == "project_revision"
