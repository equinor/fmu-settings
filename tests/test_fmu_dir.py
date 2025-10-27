"""Tests for the ProjectFMUDirectory class."""

import inspect
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest import MonkeyPatch

from fmu.settings import __version__, find_nearest_fmu_directory, get_fmu_directory
from fmu.settings._fmu_dir import (
    FMUDirectoryBase,
    ProjectFMUDirectory,
    UserFMUDirectory,
)
from fmu.settings._readme_texts import PROJECT_README_CONTENT, USER_README_CONTENT
from fmu.settings._resources.lock_manager import DEFAULT_LOCK_TIMEOUT, LockManager


def test_init_existing_directory(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests initializing an ProjectFMUDirectory on an existing .fmu directory."""
    fmu = ProjectFMUDirectory(fmu_dir.base_path)
    assert fmu.path == fmu_dir.path
    assert fmu.base_path == fmu_dir.base_path


def test_get_fmu_directory(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests initializing an ProjectFMUDirectory via get_fmu_directory."""
    fmu = get_fmu_directory(fmu_dir.base_path)
    assert fmu.path == fmu_dir.path
    assert fmu.base_path == fmu_dir.base_path


def test_find_nearest_fmu_directory(
    monkeypatch: MonkeyPatch, fmu_dir: ProjectFMUDirectory
) -> None:
    """Tests initializing an ProjectFMUDirectory via find_nearest_fmu_directory."""
    subdir = fmu_dir.path / "subdir"
    subdir.mkdir()
    subdir2 = fmu_dir.path / "subdir2"
    subdir2.mkdir()
    subsubdir = subdir / "subsubdir"
    subsubdir.mkdir()

    fmu = find_nearest_fmu_directory(str(subsubdir))
    assert fmu.path == fmu_dir.path
    assert fmu.base_path == fmu_dir.base_path

    monkeypatch.chdir(fmu_dir.base_path)
    fmu = find_nearest_fmu_directory()
    assert fmu.path == fmu_dir.path
    assert fmu.base_path == fmu_dir.base_path

    monkeypatch.chdir(subdir2)
    fmu = find_nearest_fmu_directory()
    assert fmu.path == fmu_dir.path
    assert fmu.base_path == fmu_dir.base_path


def test_init_on_missing_directory(tmp_path: Path) -> None:
    """Tests initializing with a missing directory raises."""
    with pytest.raises(
        FileNotFoundError, match=f"No .fmu directory found at {tmp_path}"
    ):
        ProjectFMUDirectory(tmp_path)


def test_init_when_fmu_is_not_a_directory(tmp_path: Path) -> None:
    """Tests initialized on a .fmu non-directory raises."""
    (tmp_path / ".fmu").touch()
    with pytest.raises(
        FileExistsError, match=f".fmu exists at {tmp_path} but is not a directory"
    ):
        ProjectFMUDirectory(tmp_path)


def test_find_fmu_directory(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests find_fmu_directory method on nested children."""
    child = fmu_dir.base_path / "child"
    grand_child = child / "grandchild"
    grand_child.mkdir(parents=True)

    found_dir = ProjectFMUDirectory.find_fmu_directory(grand_child)
    assert found_dir == fmu_dir.path


def test_find_fmu_directory_not_found(tmp_path: Path) -> None:
    """Tests find_fmu_directory() returns None if no .fmu found."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    found_dir = ProjectFMUDirectory.find_fmu_directory(empty_dir)
    assert found_dir is None


def test_find_nearest(fmu_dir: ProjectFMUDirectory) -> None:
    """Test find_nearest factory method."""
    subdir = fmu_dir.base_path / "subdir"
    subdir.mkdir()

    fmu = ProjectFMUDirectory.find_nearest(subdir)
    assert fmu.path == fmu_dir.path


def test_find_nearest_not_found(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test find_nearest raises FileNotFoundError when not found."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(
        FileNotFoundError, match=f"No .fmu directory found at or above {tmp_path}"
    ):
        ProjectFMUDirectory.find_nearest()
    with pytest.raises(
        FileNotFoundError, match=f"No .fmu directory found at or above {tmp_path}"
    ):
        ProjectFMUDirectory.find_nearest(tmp_path)


def test_cache_property_returns_cached_manager(fmu_dir: ProjectFMUDirectory) -> None:
    """Cache manager should be memoized and ready for use."""
    cache = fmu_dir.cache

    assert cache is fmu_dir.cache
    assert fmu_dir._cache_manager is cache
    assert cache.max_revisions == 5  # noqa: PLR2004


def test_set_cache_max_revisions_updates_manager(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Changing retention should update the existing cache manager."""
    cache = fmu_dir.cache
    fmu_dir.cache_max_revisions = 7

    assert cache.max_revisions == 7  # noqa: PLR2004


def test_get_config_value(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests get_config_value retrieves correctly from the config."""
    assert fmu_dir.get_config_value("version") == __version__
    assert fmu_dir.get_config_value("created_by") == "user"


def test_set_config_value(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests set_config_value sets and writes the result."""
    fmu_dir.set_config_value("version", "200.0.0")
    with open(fmu_dir.config.path, encoding="utf-8") as f:
        config_dict = json.loads(f.read())

    assert config_dict["version"] == "200.0.0"
    assert fmu_dir.get_config_value("version") == "200.0.0"
    assert fmu_dir.config.load().version == "200.0.0"


def test_update_config(fmu_dir: ProjectFMUDirectory) -> None:
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


def test_update_config_invalid_data(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that update_config raises ValidationError on bad data."""
    updates = {"version": 123}
    with pytest.raises(
        ValueError,
        match=f"Invalid value set for 'ProjectConfigManager' with updates '{updates}'",
    ):
        fmu_dir.update_config(updates)


def test_get_file_path(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests get_file_path returns correct path."""
    path = fmu_dir.get_file_path("test.txt")
    assert path == fmu_dir.path / "test.txt"


def test_file_exists(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests file_exists returns correct boolean."""
    test_file = fmu_dir.path / "exists.txt"
    test_file.touch()

    assert fmu_dir.file_exists("exists.txt") is True
    assert fmu_dir.file_exists("doesnt.txt") is False


def test_read_file(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests read_file reads bytes correctly."""
    test_file = fmu_dir.path / "bin.dat"
    test_data = b"test bin data"
    test_file.write_bytes(test_data)

    data = fmu_dir.read_file("bin.dat")
    assert data == test_data


def test_read_file_not_found(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests read_file raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError, match="No such file or directory"):
        fmu_dir.read_file("not_real.txt")


def test_read_text_file(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests read_text_file reads text correctly."""
    test_file = fmu_dir.path / "text.txt"
    test_text = "test text data å"
    test_file.write_text(test_text)

    text = fmu_dir.read_text_file("text.txt")
    assert text == test_text


def test_write_text_file(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests write_text_file writes text correctly."""
    test_text = "new text data æ"
    fmu_dir.write_text_file("new_text.txt", test_text)

    file_path = fmu_dir.path / "new_text.txt"
    assert file_path.exists()
    assert file_path.read_text() == test_text


def test_write_file_creates_dir(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests write_file creates parent directories."""
    test_data = b"nested data"
    fmu_dir.write_file("nested/dir/file.dat", test_data)

    nested_dir = fmu_dir.path / "nested" / "dir"
    assert nested_dir.is_dir()

    file_path = nested_dir / "file.dat"
    assert file_path.exists()
    assert file_path.read_bytes() == test_data


def test_write_operations_raise_when_locked(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests write helpers raise when another process holds the lock."""
    lock = LockManager(fmu_dir)
    with (
        patch("socket.gethostname", return_value="other-host"),
        patch("os.getpid", return_value=12345),
    ):
        lock.acquire()

    with pytest.raises(PermissionError, match="Cannot write to .fmu directory"):
        fmu_dir.write_text_file("blocked.txt", "blocked")

    with pytest.raises(PermissionError, match="Cannot write to .fmu directory"):
        fmu_dir.write_file("blocked.bin", b"blocked")

    with (
        patch("socket.gethostname", return_value="other-host"),
        patch("os.getpid", return_value=12345),
    ):
        lock.release()


def test_list_files(fmu_dir: ProjectFMUDirectory) -> None:
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


def test_ensure_directory(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that ensure_directory creates directories."""
    dir_path = fmu_dir.ensure_directory("nested/test/dir")
    assert dir_path.exists()
    assert dir_path.is_dir()


def test_user_init_existing_directory(user_fmu_dir: UserFMUDirectory) -> None:
    """Tests initializing an ProjectFMUDirectory on an existing .fmu directory."""
    with patch("pathlib.Path.home", return_value=user_fmu_dir.base_path):
        fmu = UserFMUDirectory()

    assert fmu.path == user_fmu_dir.path
    assert fmu.base_path == user_fmu_dir.base_path


def test_user_init_on_missing_directory(tmp_path: Path) -> None:
    """Tests initializing with a missing directory raises."""
    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        pytest.raises(
            FileNotFoundError, match=f"No .fmu directory found at {tmp_path}"
        ),
    ):
        UserFMUDirectory()


def test_user_init_when_fmu_is_not_a_directory(tmp_path: Path) -> None:
    """Tests initialized on a .fmu non-directory raises."""
    (tmp_path / ".fmu").touch()
    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        pytest.raises(
            FileExistsError, match=f".fmu exists at {tmp_path} but is not a directory"
        ),
    ):
        UserFMUDirectory()


def test_update_user_config(user_fmu_dir: UserFMUDirectory) -> None:
    """Tests update_config updates and saves the user config for multiple values."""
    recent_dir = "/foo/bar"
    updated_config = user_fmu_dir.update_config(
        {"version": "2.0.0", "recent_project_directories": [recent_dir]}
    )

    assert updated_config.version == "2.0.0"
    assert updated_config.recent_project_directories == [Path(recent_dir)]

    assert user_fmu_dir.config.load() is not None
    assert user_fmu_dir.get_config_value("version", None) == "2.0.0"
    assert user_fmu_dir.get_config_value("recent_project_directories") == [
        Path(recent_dir)
    ]

    config_file = user_fmu_dir.config.path
    with open(config_file, encoding="utf-8") as f:
        saved_config = json.load(f)

    assert saved_config["version"] == "2.0.0"
    assert saved_config["recent_project_directories"] == [recent_dir]


def test_update_user_config_invalid_data(user_fmu_dir: UserFMUDirectory) -> None:
    """Tests that update_config raises ValidationError on bad data."""
    updates = {"recent_project_directories": [123]}
    with pytest.raises(
        ValueError,
        match="Invalid value set for 'UserConfigManager' with updates "
        "'{'recent_project_directories':",
    ):
        user_fmu_dir.update_config(updates)


def test_update_user_config_non_unique_recent_projects(
    user_fmu_dir: UserFMUDirectory,
) -> None:
    """Tests that update_config raises on non-unique recent_project_directories."""
    updates = {"recent_project_directories": [Path("/foo/bar"), Path("/foo/bar")]}
    with pytest.raises(ValueError, match="unique entries"):
        user_fmu_dir.update_config(updates)


def test_acquire_lock_on_project_fmu(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that a lock can be acquired on the project dir."""
    fmu_dir._lock.acquire()
    assert fmu_dir._lock.is_acquired()
    assert fmu_dir._lock.exists
    assert (fmu_dir.path / ".lock").exists()


def test_acquire_lock_on_user_fmu(
    user_fmu_dir: UserFMUDirectory,
) -> None:
    """Tests that a lock can be acquired on the user dir."""
    user_fmu_dir._lock.acquire()
    assert user_fmu_dir._lock.is_acquired()
    assert user_fmu_dir._lock.exists
    assert (user_fmu_dir.path / ".lock").exists()


def test_restore_rebuilds_project_fmu_from_cache(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that restore should recreate missing files using cached config data."""
    fmu_dir.update_config({"version": "123.4.5"})
    cached_dump = json.loads((fmu_dir.path / "config.json").read_text())

    shutil.rmtree(fmu_dir.path)
    assert not fmu_dir.path.exists()

    fmu_dir.restore()

    assert fmu_dir.path.exists()
    readme_path = fmu_dir.path / "README"
    assert readme_path.exists()
    assert readme_path.read_text() == PROJECT_README_CONTENT

    restored_dump = json.loads((fmu_dir.path / "config.json").read_text())
    assert restored_dump == cached_dump

    cache_dir = fmu_dir.path / "cache" / "config"
    assert cache_dir.is_dir()
    assert any(cache_dir.iterdir())


def test_restore_resets_when_cache_missing(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that restore should fall back to reset when no cached config exists."""
    fmu_dir.config._cache = None
    shutil.rmtree(fmu_dir.path)
    assert not fmu_dir.path.exists()

    with patch.object(
        fmu_dir.config, "reset", wraps=fmu_dir.config.reset
    ) as mock_reset:
        fmu_dir.restore()

    mock_reset.assert_called_once()
    assert fmu_dir.path.exists()
    readme_path = fmu_dir.path / "README"
    assert readme_path.exists()
    assert readme_path.read_text() == PROJECT_README_CONTENT
    assert (fmu_dir.config.path).exists()


def test_restore_rebuilds_user_fmu(user_fmu_dir: UserFMUDirectory) -> None:
    """Tests that user FMU restore should recreate missing files using cached state."""
    cached_dump = json.loads((user_fmu_dir.path / "config.json").read_text())

    shutil.rmtree(user_fmu_dir.path)
    assert not user_fmu_dir.path.exists()

    user_fmu_dir.restore()

    assert user_fmu_dir.path.exists()
    readme_path = user_fmu_dir.path / "README"
    assert readme_path.exists()
    assert readme_path.read_text() == USER_README_CONTENT

    restored_dump = json.loads((user_fmu_dir.path / "config.json").read_text())
    assert restored_dump == cached_dump


def test_fmu_directory_base_exposes_lock_timeout_kwarg() -> None:
    """Tests that the kw-only lock timeout argument remains available."""
    signature = inspect.signature(FMUDirectoryBase.__init__)
    lock_timeout = signature.parameters.get("lock_timeout_seconds")

    assert lock_timeout is not None, "lock_timeout_seconds kwarg missing from base init"
    assert lock_timeout.kind is inspect.Parameter.KEYWORD_ONLY
    assert lock_timeout.default == DEFAULT_LOCK_TIMEOUT
