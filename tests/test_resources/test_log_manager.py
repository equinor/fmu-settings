"""Tests for LogManager."""

from pathlib import Path
from typing import Self

import pytest
from pydantic import BaseModel

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.log_manager import LogManager
from fmu.settings.models._enums import FilterType
from fmu.settings.models.log import Filter, Log


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
