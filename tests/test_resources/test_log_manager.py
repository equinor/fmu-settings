"""Tests for LogManager."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Self

import pytest
from pydantic import BaseModel

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.log_manager import LogManager
from fmu.settings.models._enums import FilterType
from fmu.settings.models.log import Filter, Log


class MixedLogEntry(BaseModel):
    """Log entry with fields for testing all filter types."""

    user: str = "test_user"
    timestamp: datetime = datetime(2026, 1, 1, tzinfo=UTC)
    count: int = 1


class MixedLogManager(LogManager[MixedLogEntry]):
    """Log manager with fields for testing all filter types."""

    def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initializes the mixed log manager."""
        super().__init__(fmu_dir, Log[MixedLogEntry])

    @property
    def relative_path(self: Self) -> Path:
        """Returns the relative path to the mixed log file."""
        return Path("logs") / "mixedlog.json"


def test_log_manager_instantiation(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests basic facts about the LogManager."""

    class TestEntry(BaseModel):
        user: str = "test_user"

    class TestManager(LogManager[TestEntry]):
        def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
            super().__init__(fmu_dir, Log[TestEntry])

        @property
        def relative_path(self: Self) -> Path:
            return Path("logs") / "testlog.json"

    test_manager = TestManager(fmu_dir)
    assert test_manager._cached_dataframe is None
    assert test_manager.model_class == Log[TestEntry]
    with pytest.raises(
        FileNotFoundError, match="Resource file for 'TestManager' not found"
    ):
        test_manager.load()

    test_entry = TestEntry()
    test_manager.add_log_entry(test_entry)
    assert test_manager.exists
    assert test_manager.load()[0] == test_entry


def test_changelog_filtering_on_numbers(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests filtering log when filter type is a number."""

    class NumberLogEntry(BaseModel):
        count: int = 1
        user: str = "test_user"
        data: str = "some_data"

    class NumberLogManager(LogManager[NumberLogEntry]):
        def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
            super().__init__(fmu_dir, Log[NumberLogEntry])

        @property
        def relative_path(self: Self) -> Path:
            return Path("logs") / "logwithnumber.json"

    first_log_entry = NumberLogEntry()
    second_log_entry = NumberLogEntry()
    second_log_entry.count = 2
    third_log_entry = NumberLogEntry()
    third_log_entry.count = 3
    log_manager = NumberLogManager(fmu_dir=fmu_dir)
    log_manager.add_log_entry(first_log_entry)
    log_manager.add_log_entry(second_log_entry)
    log_manager.add_log_entry(third_log_entry)
    assert log_manager.exists

    filter_value = 3
    filter: Filter = Filter(
        field_name="count",
        filter_value=str(filter_value),
        filter_type=FilterType.number,
        operator="==",
    )
    filtered_log = log_manager.filter_log(filter)
    assert len(filtered_log) == 1
    assert all(entry.count == filter_value for entry in filtered_log)

    filter.operator = "!="
    filtered_log = log_manager.filter_log(filter)
    expected_log_entries = 2
    assert len(filtered_log) == expected_log_entries
    assert all(entry.count != filter_value for entry in filtered_log)

    filter.operator = "<="
    filtered_log = log_manager.filter_log(filter)
    expected_log_entries = 3
    assert len(filtered_log) == expected_log_entries
    assert all(entry.count <= filter_value for entry in filtered_log)

    filter.operator = ">="
    filtered_log = log_manager.filter_log(filter)
    assert len(filtered_log) == 1
    assert all(entry.count >= filter_value for entry in filtered_log)


def test_filtering_empty_log_returns_empty_log(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests filtering an existing empty log."""
    log_manager = MixedLogManager(fmu_dir=fmu_dir)
    log_manager.save(Log[MixedLogEntry]([]))

    filtered_log = log_manager.filter_log(
        Filter(
            field_name="user",
            filter_value="test_user",
            filter_type=FilterType.text,
            operator="==",
        )
    )

    assert filtered_log.__class__ is log_manager.model_class
    assert len(filtered_log) == 0


def test_filtering_unknown_field_raises_value_error(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests filtering on fields that are not part of the log entry model."""
    log_manager = MixedLogManager(fmu_dir=fmu_dir)
    log_manager.add_log_entry(MixedLogEntry())

    with pytest.raises(ValueError, match="unknown"):
        log_manager.filter_log(
            Filter(
                field_name="unknown",
                filter_value="test_user",
                filter_type=FilterType.text,
                operator="==",
            )
        )


@pytest.mark.parametrize(
    ("field_name", "filter_value", "filter_type"),
    [
        ("user", "10", FilterType.number),
        ("user", "2026-01-01T00:00:00+00:00", FilterType.date),
        ("timestamp", "2026-01-01T00:00:00+00:00", FilterType.text),
        ("timestamp", "10", FilterType.number),
        ("count", "1", FilterType.text),
        ("count", "2026-01-01T00:00:00+00:00", FilterType.date),
    ],
)
def test_filtering_with_incompatible_filter_type_raises_value_error(
    fmu_dir: ProjectFMUDirectory,
    field_name: str,
    filter_value: str,
    filter_type: FilterType,
) -> None:
    """Tests filter type validation against the selected model field."""
    log_manager = MixedLogManager(fmu_dir=fmu_dir)
    log_manager.add_log_entry(MixedLogEntry())

    with pytest.raises(ValueError, match=field_name):
        log_manager.filter_log(
            Filter(
                field_name=field_name,
                filter_value=filter_value,
                filter_type=filter_type,
                operator=">",
            )
        )
