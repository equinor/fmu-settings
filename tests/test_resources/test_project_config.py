"""Tests for fmu.resources.config."""

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fmu.datamodels.fmu_results.fields import Access, Model, Smda

from fmu.settings._fmu_dir import ProjectFMUDirectory, UserFMUDirectory
from fmu.settings._resources.config_managers import (
    ProjectConfigManager,
    UserConfigManager,
)
from fmu.settings.models._enums import ChangeType
from fmu.settings.models.project_config import ProjectConfig
from fmu.settings.models.user_config import UserConfig


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


def test_config_resource_manager(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests basic facts about the ProjectConfig resource manager."""
    # This manager already exists in 'fmu_dir', but just to
    # try from scratch.
    manager = ProjectConfigManager(fmu_dir)

    assert manager.fmu_dir == fmu_dir
    assert manager.model_class == ProjectConfig
    assert manager._cache is None
    # Resource manager requires this to be implemented
    assert manager.relative_path == Path("config.json")
    assert manager.path == fmu_dir.path / manager.relative_path


def test_user_config_resource_manager(user_fmu_dir: UserFMUDirectory) -> None:
    """Tests basic facts about the ProjectConfig resource manager."""
    # This manager already exists in 'fmu_dir', but just to
    # try from scratch.
    manager = UserConfigManager(user_fmu_dir)

    assert manager.fmu_dir == user_fmu_dir
    assert manager.model_class == UserConfig
    assert manager._cache is None
    # Resource manager requires this to be implemented
    assert manager.relative_path == Path("config.json")
    assert manager.path == user_fmu_dir.path / manager.relative_path


def test_load_config(
    fmu_dir: ProjectFMUDirectory,
    config_model: ProjectConfig,
) -> None:
    """Tests that load() works when a configuration exists."""
    assert fmu_dir.config.load() == config_model
    assert fmu_dir.config._cache == config_model


def test_load_user_config(
    user_fmu_dir: UserFMUDirectory,
    user_config_model: UserConfig,
) -> None:
    """Tests that load() works when a user configuration exists."""
    assert user_fmu_dir.config.load() == user_config_model
    assert user_fmu_dir.config._cache == user_config_model


def test_get_config_missing_file(tmp_path: Path) -> None:
    """Tests get_config raises FileNotFoundError when config.json missing."""
    empty_fmu_dir = tmp_path / ".fmu"
    empty_fmu_dir.mkdir()

    fmu_dir = ProjectFMUDirectory(tmp_path)

    assert fmu_dir.config.exists is False
    with pytest.raises(
        FileNotFoundError,
        match=(
            "Resource file for 'ProjectConfigManager' not found at: "
            f"'{empty_fmu_dir}/config.json'"
        ),
    ):
        fmu_dir.config.load()


def test_get_config_invalid_json(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests a corrupted config.json raises ValueError."""
    config_path = fmu_dir.path / "config.json"
    with open(config_path, "a", encoding="utf-8") as f:
        f.write("%")

    with pytest.raises(
        ValueError, match="Invalid JSON in resource file for 'ProjectConfigManager'"
    ):
        fmu_dir.config.load(force=True)


def test_get_dot_notation_key(
    nested_dict: dict[str, Any], fmu_dir: ProjectFMUDirectory
) -> None:
    """Tests the get helper function for dot notation works as expected."""
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.c") == "2"
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.d") == {"e": 3}
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.d.e") == 3  # noqa PLR2004
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.z") is None
    assert fmu_dir.config._get_dot_notation_key(nested_dict, "b.z", "foo") == "foo"


def test_get_key(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests getting a key on configuration."""
    assert fmu_dir.config.get("created_by") == "user"
    # No nested entries exist in config yet.
    assert fmu_dir.config.get("does.not.exist", "foo") == "foo"
    assert fmu_dir.config.get("notreal", "foo") == "foo"


def test_get_key_config_does_not_exist(tmp_path: Path) -> None:
    """Tests getting a key when the config is missing."""
    empty_fmu_dir = tmp_path / ".fmu"
    empty_fmu_dir.mkdir()

    fmu_dir = ProjectFMUDirectory(tmp_path)

    assert fmu_dir.config.exists is False
    with pytest.raises(
        FileNotFoundError,
        match=(
            "Resource file for 'ProjectConfigManager' not found at: "
            f"'{empty_fmu_dir}/config.json'"
        ),
    ):
        fmu_dir.config.get("version")


def test_set_dot_notation_key(
    nested_dict: dict[str, Any], fmu_dir: ProjectFMUDirectory
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


def test_set_key(fmu_dir: ProjectFMUDirectory) -> None:
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
        match=(
            "Invalid value set for 'ProjectConfigManager' with key 'version', "
            "value '2.0'"
        ),
    ):
        fmu_dir.config.set("version", 2.0)


def test_set_key_config_does_not_exist(tmp_path: Path) -> None:
    """Tests getting a key when the config is missing."""
    empty_fmu_dir = tmp_path / ".fmu"
    empty_fmu_dir.mkdir()

    fmu_dir = ProjectFMUDirectory(tmp_path)

    assert fmu_dir.config.exists is False
    with pytest.raises(
        FileNotFoundError,
        match=(
            "Resource file for 'ProjectConfigManager' not found at: "
            f"'{empty_fmu_dir}/config.json'"
        ),
    ):
        fmu_dir.config.set("version", "200.0.0")


def test_update_config(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests setting a key on configuration."""
    fmu_dir.config.update({"created_by": "user2", "version": "200.0.0", "not.real": 0})
    assert fmu_dir.config.get("created_by") == "user2"
    assert fmu_dir.config.get("version") == "200.0.0"
    assert fmu_dir.config.get("not") is None

    bad_updates = {"created_by": {}, "version": "major"}
    with pytest.raises(
        ValueError,
        match="Invalid value set for 'ProjectConfigManager' with updates "
        f"'{bad_updates}'",
    ):
        fmu_dir.config.update(bad_updates)


def test_update_config_writes_to_changelog(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that config updates are written to changelog."""
    fmu_dir.config.update({"created_by": "user2", "version": "200.0.0", "new.field": 0})
    changelog = fmu_dir._changelog.load()
    expected_log_entries = 3
    assert len(changelog) == expected_log_entries
    assert changelog[0].change_type == ChangeType.update
    assert changelog[0].key == "created_by"
    assert changelog[0].file == "config.json"
    assert changelog[2].change_type == ChangeType.add
    assert changelog[2].key == "new.field"
    assert changelog[2].file == "config.json"


def test_set_smda(
    fmu_dir: ProjectFMUDirectory, masterdata_dict: dict[str, Any]
) -> None:
    """Tests setting the masterdata.smda value in the config."""
    assert fmu_dir.config.get("masterdata.smda") is None
    with open(fmu_dir.path / fmu_dir.config.relative_path, encoding="utf-8") as f:
        config_on_disk = json.loads(f.read())
    assert config_on_disk["masterdata"] is None

    fmu_dir.set_config_value("masterdata", masterdata_dict)

    smda_model = Smda.model_validate(masterdata_dict["smda"])
    # Compare to round-trip'd Pydantic model for uuid-str to UUID() obj conversion
    assert fmu_dir.get_config_value("masterdata.smda") == smda_model.model_dump()
    with open(fmu_dir.path / fmu_dir.config.relative_path, encoding="utf-8") as f:
        config_on_disk = json.loads(f.read())

    config_on_disk_model = ProjectConfig.model_validate(config_on_disk)
    assert fmu_dir.config._cache is not None
    assert fmu_dir.config._cache.masterdata is not None
    assert fmu_dir.config._cache.masterdata.smda == smda_model
    assert config_on_disk_model == fmu_dir.config._cache


def test_set_config_writes_to_changelog(
    fmu_dir: ProjectFMUDirectory, masterdata_dict: dict[str, Any]
) -> None:
    """Tests setting a config value writes update to changelog."""
    fmu_dir.set_config_value("masterdata", masterdata_dict)
    changelog = fmu_dir._changelog.load()
    assert changelog[0].key == "masterdata"
    assert changelog[0].change_type == ChangeType.update
    assert changelog[0].file == "config.json"

    field = fmu_dir.get_config_value("masterdata.smda.field")
    new_field = copy.deepcopy(field)
    new_field[0]["identifier"] = "test"

    fmu_dir.set_config_value("masterdata.smda.field", new_field)
    changelog = fmu_dir._changelog.load()
    expected_log_entries = 2
    assert len(changelog) == expected_log_entries
    assert changelog[1].key == "masterdata.smda.field"
    assert changelog[1].change_type == ChangeType.update
    assert changelog[1].file == "config.json"


def test_set_model_invalid_fails(
    fmu_dir: ProjectFMUDirectory, model_dict: dict[str, Any]
) -> None:
    """Tests setting the model value in the config using an invalid dictionary."""
    assert fmu_dir.config.get("model") is None

    # drop model.name to test validation
    model_dict.pop("name")

    with pytest.raises(ValueError, match="model.name"):
        fmu_dir.set_config_value("model", model_dict)


def test_set_model(fmu_dir: ProjectFMUDirectory, model_dict: dict[str, Any]) -> None:
    """Tests setting the model value in the config."""
    assert fmu_dir.config.get("model") is None
    with open(fmu_dir.path / fmu_dir.config.relative_path, encoding="utf-8") as f:
        config_on_disk = json.loads(f.read())
    assert config_on_disk["model"] is None

    fmu_dir.set_config_value("model", model_dict)

    model = Model.model_validate(model_dict)

    assert fmu_dir.get_config_value("model") == model
    assert fmu_dir.get_config_value("model.revision") == "21.0.0"
    assert fmu_dir.get_config_value("model.name") == "Drogon"

    with open(fmu_dir.path / fmu_dir.config.relative_path, encoding="utf-8") as f:
        config_on_disk = json.loads(f.read())

    config_on_disk_model = ProjectConfig.model_validate(config_on_disk)
    assert fmu_dir.config._cache is not None
    assert fmu_dir.config._cache.model == model
    assert config_on_disk_model == fmu_dir.config._cache


def test_set_access_invalid_fails(
    fmu_dir: ProjectFMUDirectory, access_dict: dict[str, Any]
) -> None:
    """Tests setting the access value in the config using an invalid dictionary."""
    assert fmu_dir.config.get("access") is None

    # drop access.asset to test validation
    access_dict.pop("asset")

    with pytest.raises(ValueError, match="access.asset"):
        fmu_dir.set_config_value("access", access_dict)


def test_set_access(fmu_dir: ProjectFMUDirectory, access_dict: dict[str, Any]) -> None:
    """Tests setting the access value in the config."""
    assert fmu_dir.config.get("access") is None
    with open(fmu_dir.path / fmu_dir.config.relative_path, encoding="utf-8") as f:
        config_on_disk = json.loads(f.read())
    assert config_on_disk["access"] is None

    fmu_dir.set_config_value("access", access_dict)

    access = Access.model_validate(access_dict)

    assert fmu_dir.get_config_value("access") == access
    assert fmu_dir.get_config_value("access.classification") == "internal"
    assert fmu_dir.get_config_value("access.asset.name") == "Drogon"

    with open(fmu_dir.path / fmu_dir.config.relative_path, encoding="utf-8") as f:
        config_on_disk = json.loads(f.read())

    config_on_disk_model = ProjectConfig.model_validate(config_on_disk)
    assert fmu_dir.config._cache is not None
    assert fmu_dir.config._cache.access == access
    assert config_on_disk_model == fmu_dir.config._cache


def test_update_config_when_it_does_not_exist(tmp_path: Path) -> None:
    """Tests getting a key when the config is missing."""
    empty_fmu_dir = tmp_path / ".fmu"
    empty_fmu_dir.mkdir()

    fmu_dir = ProjectFMUDirectory(tmp_path)

    assert fmu_dir.config.exists is False
    with pytest.raises(
        FileNotFoundError,
        match=(
            "Resource file for 'ProjectConfigManager' not found at: "
            f"'{empty_fmu_dir}/config.json'"
        ),
    ):
        fmu_dir.config.update({"created_by": "user", "version": "200.0.0"})


def test_save(fmu_dir: ProjectFMUDirectory, config_dict: dict[str, Any]) -> None:
    """Tests that save functions as expected."""
    config = fmu_dir.config.load()
    assert fmu_dir.config._cache == config
    assert config.created_by == "user"

    config_dict["created_by"] = "user2"
    new_config = ProjectConfig.model_validate(config_dict)
    fmu_dir.config.save(new_config)

    assert fmu_dir.config._cache == new_config
    with open(fmu_dir.config.path, encoding="utf-8") as f:
        new_config_dict = json.loads(f.read())

    # Patch the raw datetime string from json
    new_config_dict["created_at"] = datetime.fromisoformat(
        new_config_dict["created_at"]
    )
    assert config_dict == new_config_dict
