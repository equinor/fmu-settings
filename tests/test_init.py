"""Tests for fmu.settings._create."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pytest import MonkeyPatch

from fmu.settings import __version__
from fmu.settings._init import (
    _README,
    _create_config_model,
    _create_fmu_directory,
    init_fmu_directory,
    write_fmu_config,
)
from fmu.settings.models.config import Config


def test_create_fmu_directory_with_no_config_data(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    config_data_options: Config | dict[str, Any] | None,
    unix_epoch_utc: datetime,
) -> None:
    """Tests creating a config directory with default settings."""
    with patch("fmu.settings._init.getpass.getuser", return_value="user"):
        init_fmu_directory(tmp_path, config_data_options)

    fmu_dir = tmp_path / ".fmu"
    assert fmu_dir.exists()
    assert fmu_dir.is_dir()
    assert fmu_dir == tmp_path / ".fmu"

    config_file = fmu_dir / "config.json"
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


def test_create_fmu_config(
    config_data_options: Config | dict[str, Any] | None,
    unix_epoch_utc: datetime,
) -> None:
    """Tests that the _create_fmu_config function works as expected."""
    with (
        patch("fmu.settings._init.getpass.getuser", return_value="user"),
        patch("fmu.settings._init.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = unix_epoch_utc
        mock_datetime.datetime.now.return_value = unix_epoch_utc

        fmu_config = _create_config_model(config_data_options)

    expected = Config(
        version=__version__,
        created_at=unix_epoch_utc,
        created_by="user",
    )
    assert fmu_config == expected


def test_make_fmu_directory(tmp_path: Path) -> None:
    """Tests making the .fmu directory raises appropriate exceptions."""
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


def test_write_fmu_config_roundtrip(tmp_path: Path, config_model: Config) -> None:
    """Tests that the FMU config writes correctly."""
    config_path = write_fmu_config(tmp_path, config_model)
    assert str(config_path).endswith("config.json")
    with open(config_path, encoding="utf-8") as f:
        config_data = json.loads(f.read())
    # Fails if invalid
    Config.model_validate(config_data)


def test_readme_is_written(tmp_path: Path, config_model: Config) -> None:
    """Tests that the README is written when .fmu is initialized."""
    fmu_dir = init_fmu_directory(tmp_path, config_model)

    readme = fmu_dir.path / "README"
    assert readme.exists()
    assert readme.read_text() == _README
