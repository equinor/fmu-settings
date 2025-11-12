"""Tests for fmu.settings.resources.managers."""

import json
import shutil
from pathlib import Path
from typing import Self
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.lock_manager import LockManager
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


def test_pydantic_resource_manager_save_raises_when_locked(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests saving raises when another process holds the lock."""
    lock = LockManager(fmu_dir)
    with (
        patch("socket.gethostname", return_value="other-host"),
        patch("os.getpid", return_value=12345),
    ):
        lock.acquire()

    a = AManager(fmu_dir)
    with pytest.raises(PermissionError, match="Cannot write to .fmu directory"):
        a.save(A(foo="bar"))

    with (
        patch("socket.gethostname", return_value="other-host"),
        patch("os.getpid", return_value=12345),
    ):
        lock.release()


def test_pydantic_resource_manager_load(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests loading a Pydantic resource."""
    a = AManager(fmu_dir)
    a_model = A(foo="bar")
    a.save(a_model)
    assert a.load() == a_model
    assert a._cache == a_model


def test_pydantic_resource_manager_load_force_true(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests loading a Pydantic resource with force=True."""
    a = AManager(fmu_dir)
    a_model = A(foo="bar")
    a.save(a_model)
    assert a.load() == a_model
    assert a._cache == a_model

    a_shadow = AManager(fmu_dir)
    a_shadow_model = A(foo="baz")
    a_shadow.save(a_shadow_model)

    assert a_shadow.load() == a_shadow_model
    assert a_shadow._cache == a_shadow_model

    assert a.load() == a_model
    assert a._cache == a_model

    assert a.load(force=True) == a_shadow_model
    assert a._cache == a_shadow_model


def test_pydantic_resource_manager_load_cache_false(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests loading a Pydantic resource with cache=False."""
    a = AManager(fmu_dir)
    a_model = A(foo="bar")
    a.save(a_model)

    a_shadow = AManager(fmu_dir)
    assert a_shadow.load(store_cache=False) == a_model
    assert a_shadow._cache is None

    assert a_shadow.load(store_cache=True) == a_model
    assert a_shadow._cache == a_model


def test_pydantic_resource_manager_load_force_true_cache_false(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests loading a Pydantic resource with force=True, cache=False."""
    a = AManager(fmu_dir)
    a_model = A(foo="bar")
    a.save(a_model)

    a_shadow = AManager(fmu_dir)
    a_shadow_model = A(foo="baz")
    a_shadow.save(a_shadow_model)

    assert a.load(force=True, store_cache=False) == a_shadow_model
    assert a._cache is a_model


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


def test_pydantic_resource_manager_save_does_not_cache_when_disabled(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Saving without cache enabled should not create cache artifacts."""
    original_default = AManager.automatic_caching
    AManager.automatic_caching = False
    cache_root = fmu_dir.path / "cache"
    try:
        if cache_root.exists():
            shutil.rmtree(cache_root)
        a = AManager(fmu_dir)
        a.save(A(foo="bar"))
    finally:
        AManager.automatic_caching = original_default

    assert not cache_root.exists()


def test_pydantic_resource_manager_save_stores_revision_when_enabled(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Saving with cache enabled should persist a revision snapshot."""
    a = AManager(fmu_dir)
    model = A(foo="bar")
    a.save(model)

    cache_root = fmu_dir.path / "cache"
    assert cache_root.is_dir()
    tag_path = cache_root / "CACHEDIR.TAG"
    assert tag_path.read_text(encoding="utf-8").startswith(
        "Signature: 8a477f597d28d172789f06886806bc55"
    )

    config_cache = cache_root / "foo"
    snapshots = list(config_cache.iterdir())
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.suffix == ".json"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == model.model_dump()


def test_pydantic_resource_manager_revision_cache_trims_excess(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Revision caching should retain only the configured number of snapshots."""
    original_limit = fmu_dir.cache_max_revisions
    fmu_dir.cache_max_revisions = 5
    try:
        a = AManager(fmu_dir)
        a.save(A(foo="one"))
        a.save(A(foo="two"))
        a.save(A(foo="three"))
        a.save(A(foo="four"))
        a.save(A(foo="five"))
        a.save(A(foo="six"))
    finally:
        fmu_dir.cache_max_revisions = original_limit

    config_cache = fmu_dir.path / "cache" / "foo"
    snapshots = sorted(p.name for p in config_cache.iterdir())
    assert len(snapshots) == 5  # noqa: PLR2004

    contents = [
        json.loads((config_cache / name).read_text(encoding="utf-8"))["foo"]
        for name in snapshots
    ]
    assert contents == ["two", "three", "four", "five", "six"]
