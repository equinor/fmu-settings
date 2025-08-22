"""Tests for fmu.settings.resources.managers."""

import json
from pathlib import Path
from typing import Self

import pytest
from pydantic import BaseModel

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.pydantic_resource_manager import PydanticResourceManager


class A(BaseModel):
    """A test Pydantic class."""

    foo: str


class AManager(PydanticResourceManager[A]):
    """A test Pydantic resource manager."""

    def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initializer."""
        super().__init__(fmu_dir, A)

    @property
    def relative_path(self: Self) -> Path:
        """Relative path."""
        return Path("foo.json")


def test_pydantic_resource_manager_implementation(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that derived classes must implement 'relative_path'."""

    class Manager(PydanticResourceManager[A]):
        """A test Pydantic resource manager."""

        def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
            """Initializer."""
            super().__init__(fmu_dir, A)

    manager = Manager(fmu_dir)
    with pytest.raises(NotImplementedError):
        _ = manager.relative_path


def test_pydantic_resource_manager_init(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that initialization of a Pydantic resource manager is as expected."""
    a = AManager(fmu_dir)
    assert a.fmu_dir == fmu_dir
    assert a.model_class == A

    a_path = fmu_dir.path / "foo.json"
    assert a.path == a_path
    assert a.exists is False
    assert a._cache is None

    with pytest.raises(
        FileNotFoundError,
        match=f"Resource file for 'AManager' not found at: '{a_path}'",
    ):
        a.load()


def test_pydantic_resource_manager_save(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests saving a Pydantic resource that does not yet exist."""
    a = AManager(fmu_dir)
    a_model = A(foo="bar")

    a.save(a_model)

    assert a.exists
    assert a._cache == a_model
    with open(a.path, encoding="utf-8") as f:
        a_dict = json.loads(f.read())

    assert a_model == A.model_validate(a_dict)


def test_pydantic_resource_manager_load(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests loading a Pydantic resource."""
    a = AManager(fmu_dir)
    a_model = A(foo="bar")
    a.save(a_model)
    assert a.load() == a_model
    assert a._cache == a_model


def test_pydantic_resource_manager_loads_invalid_model(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests loading a Pydantic resource."""
    a = AManager(fmu_dir)
    a_model = A(foo="bar")
    a.save(a_model)

    a_dict = a_model.model_dump()
    a_dict["foo"] = 0

    fmu_dir.write_text_file(a.path, json.dumps(a_dict))

    with pytest.raises(
        ValueError, match=r"Invalid content in resource file[\s\S]*input_value=0"
    ):
        a.load(force=True)
