"""Tests for fmu.resources.config."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from fmu.settings._fmu_dir import FMUDirectory
from fmu.settings.resources.config import Config, ConfigManager


@pytest.fixture
def nested_dict() -> dict[str, Any]:
    """A nested dictionary to test get-set dot notation."""
    return {
        "a": 1,
        "b": {
            "c": "2",
            "d": {"e": 3},
        },
    }


def test_config_resource_manager(fmu_dir: FMUDirectory) -> None:
    """Tests basic facts about the Config resource manager."""
    # This manager already exists in 'fmu_dir', but just to
    # try from scratch.
    manager = ConfigManager(fmu_dir)

    assert manager.fmu_dir == fmu_dir
    assert manager.model_class == Config
    assert manager._cache is None
    # Resource manager requires this to be implemented
    assert manager.relative_path == Path("config.json")
    assert manager.path == fmu_dir.path / manager.relative_path


def test_load_config(
    fmu_dir: FMUDirectory,
    config_model: Config,
) -> None:
    """Tests that load() works when a configuration exists."""
    assert fmu_dir.config.load() == config_model


def test_get_config_missing_file(tmp_path: Path) -> None:
    """Tests get_config raises FileNotFoundError when config.json missing."""
    empty_fmu_dir = tmp_path / ".fmu"
    empty_fmu_dir.mkdir()

    fmu_dir = FMUDirectory(tmp_path)

    assert fmu_dir.config.exists is False
    with pytest.raises(
        FileNotFoundError,
        match=(
            "Resource file for 'ConfigManager' not found at: "
            f"'{empty_fmu_dir}/config.json'"
        ),
    ):
        fmu_dir.config.load()


def test_get_config_invalid_json(fmu_dir: FMUDirectory) -> None:
    """Tests a corrupted config.json raises ValueError."""
    config_path = fmu_dir.path / "config.json"
    with open(config_path, "a", encoding="utf-8") as f:
        f.write("%")

    with pytest.raises(
        ValueError, match="Invalid JSON in resource file for 'ConfigManager'"
    ):
        fmu_dir.config.load(force=True)


def test_get_dot_notation_key(
    nested_dict: dict[str, Any], fmu_dir: FMUDirectory
) -> None:
    """Tests the get helper function for dot notation works as expected."""
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.c") == "2"
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.d") == {"e": 3}
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.d.e") == 3  # noqa PLR2004
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.z") is None
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.z", "foo") == "foo"


def test_get_key(fmu_dir: FMUDirectory) -> None:
    """Tests getting a key on configuration."""
    assert fmu_dir.config.get("created_by") == "user"
    # No nested entries exist in config yet.
    assert fmu_dir.config.get("does.not.exist", "foo") == "foo"
    assert fmu_dir.config.get("notreal", "foo") == "foo"


def test_get_key_config_does_not_exist(tmp_path: Path) -> None:
    """Tests getting a key when the config is missing."""
    empty_fmu_dir = tmp_path / ".fmu"
    empty_fmu_dir.mkdir()

    fmu_dir = FMUDirectory(tmp_path)

    assert fmu_dir.config.exists is False
    with pytest.raises(
        FileNotFoundError,
        match=(
            "Resource file for 'ConfigManager' not found at: "
            f"'{empty_fmu_dir}/config.json'"
        ),
    ):
        fmu_dir.config.get("version")


def test_set_dot_notation_key(
    nested_dict: dict[str, Any], fmu_dir: FMUDirectory
) -> None:
    """Tests the set helper function for dot notation works as expected."""
    assert nested_dict["b"]["c"] == "2"
    fmu_dir.config._set_dot_notation_key(nested_dict, "b.c", "3")
    assert nested_dict["b"]["c"] == "3"

    assert nested_dict["b"]["d"] == {"e": 3}
    fmu_dir.config._set_dot_notation_key(nested_dict, "b.d", {"e": "s"})
    assert nested_dict["b"]["d"] == {"e": "s"}
    fmu_dir.config._set_dot_notation_key(nested_dict, "b.d.e", 3)
    assert nested_dict["b"]["d"] == {"e": 3}

    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.z") is None
    fmu_dir.config._set_dot_notation_key(nested_dict, "b.z", "foo")
    assert nested_dict["b"]["z"] == "foo"

    # Overwrites existing non-dict values
    fmu_dir.config._set_dot_notation_key(nested_dict, "a.b", {})
    assert nested_dict["a"] != 1
    assert nested_dict["a"]["b"] == {}


def test_set_key(fmu_dir: FMUDirectory) -> None:
    """Tests setting a key on configuration."""
    fmu_dir.config.set("created_by", "user2")
    assert fmu_dir.config.get("created_by") == "user2"

    config_model = fmu_dir.config.load(force=True)
    config_dict = config_model.model_dump()
    assert config_dict["created_by"] == "user2"

    # No nested entries exist in config yet.
    fmu_dir.config.set("does.not.exist", "foo")
    assert fmu_dir.config.get("does.not.exist") is None
    fmu_dir.config.set("notreal", "foo")
    assert fmu_dir.config.get("notreal") is None

    # Does not write invalid values
    config_model = fmu_dir.config.load(force=True)
    config_dict = config_model.model_dump()
    assert config_dict.get("does", None) is None
    assert config_dict.get("notreal", None) is None

    with pytest.raises(
        ValueError,
        match=("Invalid value set for 'ConfigManager' with key 'version', value '2.0'"),
    ):
        fmu_dir.config.set("version", 2.0)


def test_set_key_config_does_not_exist(tmp_path: Path) -> None:
    """Tests getting a key when the config is missing."""
    empty_fmu_dir = tmp_path / ".fmu"
    empty_fmu_dir.mkdir()

    fmu_dir = FMUDirectory(tmp_path)

    assert fmu_dir.config.exists is False
    with pytest.raises(
        FileNotFoundError,
        match=(
            "Resource file for 'ConfigManager' not found at: "
            f"'{empty_fmu_dir}/config.json'"
        ),
    ):
        fmu_dir.config.set("version", "200.0.0")


def test_update_config(fmu_dir: FMUDirectory) -> None:
    """Tests setting a key on configuration."""
    fmu_dir.config.update({"created_by": "user2", "version": "200.0.0", "not.real": 0})
    assert fmu_dir.config.get("created_by") == "user2"
    assert fmu_dir.config.get("version") == "200.0.0"
    assert fmu_dir.config.get("not") is None

    bad_updates = {"created_by": {}, "version": "major"}
    with pytest.raises(
        ValueError,
        match=f"Invalid value set for 'ConfigManager' with updates '{bad_updates}'",
    ):
        fmu_dir.config.update(bad_updates)


def test_update_config_when_it_does_not_exist(tmp_path: Path) -> None:
    """Tests getting a key when the config is missing."""
    empty_fmu_dir = tmp_path / ".fmu"
    empty_fmu_dir.mkdir()

    fmu_dir = FMUDirectory(tmp_path)

    assert fmu_dir.config.exists is False
    with pytest.raises(
        FileNotFoundError,
        match=(
            "Resource file for 'ConfigManager' not found at: "
            f"'{empty_fmu_dir}/config.json'"
        ),
    ):
        fmu_dir.config.update({"created_by": "user", "version": "200.0.0"})


def test_save(fmu_dir: FMUDirectory, config_dict: dict[str, Any]) -> None:
    """Tests that save functions as expected."""
    config = fmu_dir.config.load()
    assert fmu_dir.config._cache == config
    assert config.created_by == "user"

    config_dict["created_by"] = "user2"
    new_config = Config.model_validate(config_dict)
    fmu_dir.config.save(new_config)

    assert fmu_dir.config._cache == new_config
    with open(fmu_dir.config.path, encoding="utf-8") as f:
        new_config_dict = json.loads(f.read())

    # Patch the raw datetime string from json
    new_config_dict["created_at"] = datetime.fromisoformat(
        new_config_dict["created_at"]
    )
    assert config_dict == new_config_dict
