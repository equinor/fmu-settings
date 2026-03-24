"""Tests the module cli invocation works and is correct."""

import subprocess
from pathlib import Path

from pytest import MonkeyPatch


def test_drogon_fmu_cli_help() -> None:
    """Sanity check on the cli.

    Will raise a CalledProcessError if any error occurs.
    """
    output = subprocess.check_output(["python", "-m", "fmu.settings._drogon", "-h"])
    assert "Generate a Drogon .fmu/" in str(output)


def test_drogon_fmu_cli_defaults_to_pwd(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """CLI invocation defaults to creating the Drogon .fmu/ in the pwd."""
    monkeypatch.chdir(tmp_path)
    output = subprocess.check_output(["python", "-m", "fmu.settings._drogon"])
    assert (tmp_path / ".fmu").is_dir()
    assert str(tmp_path) in str(output)


def test_drogon_fmu_cli_writes_to_path_in_arg(tmp_path: Path) -> None:
    """CLI invocation creates the Drogon .fmu/ in a provided path."""
    output = subprocess.check_output(
        ["python", "-m", "fmu.settings._drogon", str(tmp_path)]
    )
    assert (tmp_path / ".fmu").is_dir()
    assert str(tmp_path) in str(output)
