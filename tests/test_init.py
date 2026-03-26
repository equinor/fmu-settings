"""Tests for fmu.settings._create."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from fmu.settings import __version__
from fmu.settings._global_config import find_global_config
from fmu.settings._init import (
    REQUIRED_FMU_PROJECT_SUBDIRS,
    InvalidFMUProjectPathError,
    _create_fmu_directory,
    init_fmu_directory,
    init_user_fmu_directory,
)
from fmu.settings._readme_texts import PROJECT_README_CONTENT, USER_README_CONTENT
from fmu.settings.models.project_config import ProjectConfig
from fmu.settings.models.user_config import UserConfig


def test_create_fmu_directory(tmp_path: Path) -> None:
    """Tests creating the .fmu directory raises appropriate exceptions."""
    with pytest.raises(FileNotFoundError, match="Base path '/foo' does not exist."):
        _create_fmu_directory(Path("/foo"))

    fmu_dir = tmp_path / ".fmu"
    fmu_dir.mkdir()
    with pytest.raises(FileExistsError, match=f"{fmu_dir} already exists"):
        _create_fmu_directory(tmp_path)

    fmu_dir.rmdir()
    fmu_dir.touch()
    with pytest.raises(
        FileExistsError, match=f"{fmu_dir} exists but is not a directory"
    ):
        _create_fmu_directory(tmp_path)


def test_init_fmu_directory_with_no_config_data(
    fmu_project_root: Path,
    unix_epoch_utc: datetime,
) -> None:
    """Tests initializing a .fmu directory with default settings."""
    with (
        patch(
            "fmu.settings.models.project_config.getpass.getuser",
            return_value="user",
        ),
    ):
        fmu_dir = init_fmu_directory(fmu_project_root)

    assert fmu_dir.path.exists()
    assert fmu_dir.path.is_dir()
    assert fmu_dir.path == fmu_project_root / ".fmu"

    config_file = fmu_dir.path / "config.json"
    assert config_file.exists()

    with open(config_file, encoding="utf-8") as f:
        config_json = json.load(f)

    assert config_json["version"] == __version__
    assert config_json["created_by"] == "user"
    assert config_json["created_at"] != str(unix_epoch_utc)

    created_at = datetime.fromisoformat(config_json["created_at"])
    now = datetime.now(UTC)
    one_min_ago = now - timedelta(minutes=1)
    assert one_min_ago <= created_at <= now


def test_create_fmu_directory_with_config_model(
    fmu_project_root: Path,
    config_model: ProjectConfig,
) -> None:
    """Tests initializing a .fmu directory with a ProjectConfig model."""
    config_model.version = "200.0.0"
    config_model.model_rebuild()
    fmu_dir = init_fmu_directory(fmu_project_root, config_model)
    config = fmu_dir.config.load()
    assert config.version == "200.0.0"


def test_create_fmu_directory_with_config_dict(
    fmu_project_root: Path,
    config_dict: dict[str, Any],
) -> None:
    """Tests initializing a .fmu directory with a ProjectConfig model."""
    config_dict["version"] = "200.0.0"
    fmu_dir = init_fmu_directory(fmu_project_root, config_dict)
    config = fmu_dir.config.load()
    assert config.version == "200.0.0"


def test_write_fmu_config_roundtrip(fmu_project_root: Path) -> None:
    """Tests that the FMU config writes correctly."""
    fmu_dir = init_fmu_directory(fmu_project_root)
    assert str(fmu_dir.config.path).endswith("config.json")
    with open(fmu_dir.config.path, encoding="utf-8") as f:
        config_data = json.loads(f.read())
    # Fails if invalid
    ProjectConfig.model_validate(config_data)


def test_init_fmu_directory_rejects_invalid_project_path(tmp_path: Path) -> None:
    """Tests that init reports a semantic error for non-FMU project paths."""
    required_dirs = ", ".join(f"'{dir}'" for dir in REQUIRED_FMU_PROJECT_SUBDIRS)
    expected_message = (
        "Failed initializing .fmu directory. Initialize it from a project root "
        f"containing {required_dirs}. Did not find: {required_dirs}."
    )
    with pytest.raises(InvalidFMUProjectPathError) as exc_info:
        init_fmu_directory(tmp_path)

    assert str(exc_info.value) == expected_message


def test_init_fmu_directory_force_skips_project_validation(tmp_path: Path) -> None:
    """Tests that force=True preserves init in arbitrary directories."""
    fmu_dir = init_fmu_directory(tmp_path, force=True)

    assert fmu_dir.path.exists()
    assert fmu_dir.path == tmp_path / ".fmu"


def test_init_fmu_directory_auto_finds_global_config(
    fmu_project_root: Path,
    generate_strict_valid_globalconfiguration: Any,
) -> None:
    """Tests that init automatically imports global config for valid FMU roots."""
    valid_global_config = generate_strict_valid_globalconfiguration()
    output_dir = fmu_project_root / "fmuconfig/output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "global_variables.yml").write_text(
        yaml.safe_dump(valid_global_config.model_dump(mode="json", by_alias=True))
    )

    fmu_dir = init_fmu_directory(fmu_project_root)
    config = fmu_dir.config.load()

    assert config.masterdata is not None
    assert config.masterdata == valid_global_config.masterdata
    assert config.model is not None
    assert config.model == valid_global_config.model
    assert config.access is not None
    assert config.access.asset == valid_global_config.access.asset
    assert config.access.classification == valid_global_config.access.classification


def test_init_fmu_directory_skips_invalid_auto_discovered_drogon_global_config(
    fmuconfig_with_output: Path,
) -> None:
    """Tests that auto-discovered Drogon global config is rejected and not imported."""
    for dir in REQUIRED_FMU_PROJECT_SUBDIRS:
        (fmuconfig_with_output / dir).mkdir(parents=True, exist_ok=True)

    fmu_dir = init_fmu_directory(fmuconfig_with_output)
    config = fmu_dir.config.load()

    assert fmu_dir.path.exists()
    assert config.masterdata is None
    assert config.model is None
    assert config.access is None


def test_write_fmu_config_with_global_config(fmuconfig_with_output: Path) -> None:
    """Tests creating an .fmu config with a global_config."""
    for dir in REQUIRED_FMU_PROJECT_SUBDIRS:
        (fmuconfig_with_output / dir).mkdir(parents=True, exist_ok=True)
    cfg = find_global_config(fmuconfig_with_output, strict=False)
    assert cfg is not None
    with patch("fmu.settings._init.find_global_config") as mock_find_global_config:
        fmu_dir = init_fmu_directory(fmuconfig_with_output, global_config=cfg)

    mock_find_global_config.assert_not_called()
    config = fmu_dir.config.load()
    assert config.masterdata is not None
    assert config.masterdata.smda.field[0].identifier == "DROGON"

    assert config.model is not None
    assert config.model.name == "Drogon"

    assert config.access is not None
    assert config.access.asset.name == "Drogon"


def test_readme_is_written(
    fmu_project_root: Path,
    config_model: ProjectConfig,
) -> None:
    """Tests that the README is written when .fmu is initialized."""
    fmu_dir = init_fmu_directory(fmu_project_root, config_model)

    readme = fmu_dir.path / "README"
    assert readme.exists()
    assert readme.read_text() == PROJECT_README_CONTENT


def test_init_user_fmu_directory(
    tmp_path: Path,
    unix_epoch_utc: datetime,
) -> None:
    """Tests initializing a user .fmu directory with default settings."""
    with patch("pathlib.Path.home", return_value=tmp_path):
        fmu_dir = init_user_fmu_directory()

    assert fmu_dir.path.exists()
    assert fmu_dir.path.is_dir()
    assert fmu_dir.path == tmp_path / ".fmu"

    config_file = fmu_dir.path / "config.json"
    assert config_file.exists()

    with open(config_file, encoding="utf-8") as f:
        config_json = json.load(f)

    assert config_json["version"] == __version__
    assert config_json["created_at"] != str(unix_epoch_utc)
    assert config_json["user_api_keys"] == {"smda_subscription": None}
    assert config_json["recent_project_directories"] == []

    created_at = datetime.fromisoformat(config_json["created_at"])
    now = datetime.now(UTC)
    one_min_ago = now - timedelta(minutes=1)
    assert one_min_ago <= created_at <= now


def test_write_user_fmu_config_roundtrip(tmp_path: Path) -> None:
    """Tests that the FMU config writes correctly."""
    with patch("pathlib.Path.home", return_value=tmp_path):
        fmu_dir = init_user_fmu_directory()
    assert str(fmu_dir.config.path).endswith("config.json")
    with open(fmu_dir.config.path, encoding="utf-8") as f:
        config_data = json.loads(f.read())
    # Fails if invalid
    UserConfig.model_validate(config_data)


def test_user_readme_is_written(tmp_path: Path, config_model: ProjectConfig) -> None:
    """Tests that the README is written when .fmu is initialized."""
    with patch("pathlib.Path.home", return_value=tmp_path):
        fmu_dir = init_user_fmu_directory()

    readme = fmu_dir.path / "README"
    assert readme.exists()
    assert readme.read_text() == USER_README_CONTENT
