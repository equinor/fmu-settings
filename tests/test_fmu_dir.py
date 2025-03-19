"""Tests for the FMUDirectory class."""

import json
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from fmu.settings import __version__, find_nearest_fmu_directory, get_fmu_directory
from fmu.settings._fmu_dir import FMUDirectory


def test_init_existing_directory(fmu_dir: FMUDirectory) -> None:
    """Tests initializing an FMUDirectory on an existing .fmu directory."""
    fmu = FMUDirectory(fmu_dir.base_path, search_parents=False)
    assert fmu.path == fmu_dir.path
    assert fmu.base_path == fmu_dir.base_path


def test_get_fmu_directory(fmu_dir: FMUDirectory) -> None:
    """Tests initializing an FMUDirectory via get_fmu_directory."""
    fmu = get_fmu_directory(fmu_dir.base_path, search_parents=False)
    assert fmu.path == fmu_dir.path
    assert fmu.base_path == fmu_dir.base_path


def test_init_on_missing_directory(tmp_path: Path) -> None:
    """Tests initializing with a missing directory raises."""
    with pytest.raises(
        FileNotFoundError, match=f"No .fmu directory found at {tmp_path}"
    ):
        FMUDirectory(tmp_path, search_parents=False)


def test_init_search_parents(fmu_dir: FMUDirectory) -> None:
    """Tests initializing with search_parents=True."""
    subdir = fmu_dir.base_path / "subdir"
    subdir.mkdir()

    fmu = FMUDirectory(subdir, search_parents=True)
    assert fmu.path == fmu_dir.path
    assert fmu.base_path == subdir


def test_init_search_parents_on_missing_directory(tmp_path: Path) -> None:
    """Tests initializing with a missing directory raises."""
    with pytest.raises(
        FileNotFoundError, match=f"No .fmu directory found at or above {tmp_path}"
    ):
        FMUDirectory(tmp_path, search_parents=True)


def test_find_fmu_directory(fmu_dir: FMUDirectory) -> None:
    """Tests find_fmu_directory method on nested children."""
    child = fmu_dir.base_path / "child"
    grand_child = child / "grandchild"
    grand_child.mkdir(parents=True)

    found_dir = FMUDirectory.find_fmu_directory(grand_child)
    assert found_dir == fmu_dir.path


def test_find_fmu_directory_not_found(tmp_path: Path) -> None:
    """Tests find_fmu_directory() returns None if no .fmu found."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    found_dir = FMUDirectory.find_fmu_directory(empty_dir)
    assert found_dir is None


def test_find_nearest(fmu_dir: FMUDirectory) -> None:
    """Test find_nearest factory method."""
    subdir = fmu_dir.base_path / "subdir"
    subdir.mkdir()

    fmu = FMUDirectory.find_nearest(subdir)
    assert fmu.path == fmu_dir.path


def test_find_nearest_fmu_directory(fmu_dir: FMUDirectory) -> None:
    """Test find_nearest factory method."""
    subdir = fmu_dir.base_path / "subdir"
    subdir.mkdir()

    fmu = find_nearest_fmu_directory(subdir)
    assert fmu.path == fmu_dir.path


def test_find_nearest_not_found(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test find_nearest raises FileNotFoundError when not found."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(
        FileNotFoundError, match=f"No .fmu directory found at or above {tmp_path}"
    ):
        FMUDirectory.find_nearest()
    with pytest.raises(
        FileNotFoundError, match=f"No .fmu directory found at or above {tmp_path}"
    ):
        FMUDirectory.find_nearest(tmp_path)


def test_get_config_value(fmu_dir: FMUDirectory) -> None:
    """Tests get_config_value retrieves correctly from the config."""
    assert fmu_dir.get_config_value("version") == __version__
    assert fmu_dir.get_config_value("created_by") == "user"


def test_set_config_value(fmu_dir: FMUDirectory) -> None:
    """Tests set_config_value sets and writes the result."""
    fmu_dir.set_config_value("version", "200.0.0")
    with open(fmu_dir.config.path, encoding="utf-8") as f:
        config_dict = json.loads(f.read())

    assert config_dict["version"] == "200.0.0"
    assert fmu_dir.get_config_value("version") == "200.0.0"
    assert fmu_dir.config.load().version == "200.0.0"


def test_update_config(fmu_dir: FMUDirectory) -> None:
    """Tests update_config updates and saves the config for multiple values."""
    updated_config = fmu_dir.update_config({"version": "2.0.0", "created_by": "user2"})

    assert updated_config.version == "2.0.0"
    assert updated_config.created_by == "user2"

    assert fmu_dir.config.load() is not None
    assert fmu_dir.get_config_value("version", None) == "2.0.0"
    assert fmu_dir.get_config_value("created_by", None) == "user2"

    config_file = fmu_dir.config.path
    with open(config_file, encoding="utf-8") as f:
        saved_config = json.load(f)

    assert saved_config["version"] == "2.0.0"
    assert saved_config["created_by"] == "user2"


def test_update_config_invalid_data(fmu_dir: FMUDirectory) -> None:
    """Tests that update_config raises ValidationError on bad data."""
    updates = {"version": 123}
    with pytest.raises(
        ValueError,
        match=f"Invalid value set for 'ConfigManager' with updates '{updates}'",
    ):
        fmu_dir.update_config(updates)


def test_get_file_path(fmu_dir: FMUDirectory) -> None:
    """Tests get_file_path returns correct path."""
    path = fmu_dir.get_file_path("test.txt")
    assert path == fmu_dir.path / "test.txt"


def test_file_exists(fmu_dir: FMUDirectory) -> None:
    """Tests file_exists returns correct boolean."""
    test_file = fmu_dir.path / "exists.txt"
    test_file.touch()

    assert fmu_dir.file_exists("exists.txt") is True
    assert fmu_dir.file_exists("doesnt.txt") is False


def test_read_file(fmu_dir: FMUDirectory) -> None:
    """Tests read_file reads bytes correctly."""
    test_file = fmu_dir.path / "bin.dat"
    test_data = b"test bin data"
    test_file.write_bytes(test_data)

    data = fmu_dir.read_file("bin.dat")
    assert data == test_data


def test_read_file_not_found(fmu_dir: FMUDirectory) -> None:
    """Tests read_file raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError, match="No such file or directory"):
        fmu_dir.read_file("not_real.txt")


def test_read_text_file(fmu_dir: FMUDirectory) -> None:
    """Tests read_text_file reads text correctly."""
    test_file = fmu_dir.path / "text.txt"
    test_text = "test text data å"
    test_file.write_text(test_text)

    text = fmu_dir.read_text_file("text.txt")
    assert text == test_text


def test_write_text_file(fmu_dir: FMUDirectory) -> None:
    """Tests write_text_file writes text correctly."""
    test_text = "new text data æ"
    fmu_dir.write_text_file("new_text.txt", test_text)

    file_path = fmu_dir.path / "new_text.txt"
    assert file_path.exists()
    assert file_path.read_text() == test_text


def test_write_file_creates_dir(fmu_dir: FMUDirectory) -> None:
    """Tests write_file creates parent directories."""
    test_data = b"nested data"
    fmu_dir.write_file("nested/dir/file.dat", test_data)

    nested_dir = fmu_dir.path / "nested" / "dir"
    assert nested_dir.is_dir()

    file_path = nested_dir / "file.dat"
    assert file_path.exists()
    assert file_path.read_bytes() == test_data


def test_list_files(fmu_dir: FMUDirectory) -> None:
    """Tests that list_files returns the correct files."""
    (fmu_dir.path / "file1.txt").touch()
    (fmu_dir.path / "file2.txt").touch()

    subdir = fmu_dir.path / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").touch()

    files = fmu_dir.list_files()
    filenames = [f.name for f in files]

    assert "file1.txt" in filenames
    assert "file2.txt" in filenames
    assert "config.json" in filenames

    assert "file3.txt" not in filenames

    subdir_files = fmu_dir.list_files("subdir")
    assert len(subdir_files) == 1
    assert subdir_files[0].name == "file3.txt"

    not_subdir_files = fmu_dir.list_files("not_subdir")
    assert not_subdir_files == []


def test_ensure_directory(fmu_dir: FMUDirectory) -> None:
    """Tests that ensure_directory creates directories."""
    dir_path = fmu_dir.ensure_directory("nested/test/dir")
    assert dir_path.exists()
    assert dir_path.is_dir()
    assert dir_path == fmu_dir.path / "nested" / "test" / "dir"
