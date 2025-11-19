"""Tests for fmu.settings.resources.managers."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Self
from unittest.mock import patch

import pytest
from pydantic import AwareDatetime, BaseModel

from fmu.settings._fmu_dir import ProjectFMUDirectory
from fmu.settings._resources.lock_manager import LockManager
from fmu.settings._resources.pydantic_resource_manager import (
    MutablePydanticResourceManager,
    PydanticResourceManager,
)
from fmu.settings.types import ResettableBaseModel


class PydanticResourceTest(BaseModel):
    """A test class for a Pydantic resource."""

    foo: str


class MutablePydanticResourceTest(ResettableBaseModel):
    """A test class for a mutable pydantic resource."""

    foo: str


class PydanticManagerTest(PydanticResourceManager[PydanticResourceTest]):
    """A test Pydantic resource manager."""

    def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initializer."""
        super().__init__(fmu_dir, PydanticResourceTest)

    @property
    def relative_path(self: Self) -> Path:
        """Relative path."""
        return Path("foo.json")


class MutablePydanticManagerTest(
    MutablePydanticResourceManager[MutablePydanticResourceTest]
):
    """A test mutable Pydantic resource manager."""

    def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
        """Initializer."""
        super().__init__(fmu_dir, MutablePydanticResourceTest)

    @property
    def relative_path(self: Self) -> Path:
        """Relative path."""
        return Path("mutable_foo.json")


def test_pydantic_resource_manager_implementation(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that derived classes must implement 'relative_path'."""

    class Manager(PydanticResourceManager[PydanticResourceTest]):
        """A test Pydantic resource manager."""

        def __init__(self: Self, fmu_dir: ProjectFMUDirectory) -> None:
            """Initializer."""
            super().__init__(fmu_dir, PydanticResourceTest)

    manager = Manager(fmu_dir)
    with pytest.raises(NotImplementedError):
        _ = manager.relative_path


def test_pydantic_resource_manager_init(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests that initialization of a Pydantic resource manager is as expected."""
    test_manager = PydanticManagerTest(fmu_dir)
    assert test_manager.fmu_dir == fmu_dir
    assert test_manager.model_class == PydanticResourceTest

    resource_path = fmu_dir.path / "foo.json"
    assert test_manager.path == resource_path
    assert test_manager.exists is False
    assert test_manager._cache is None

    with pytest.raises(
        FileNotFoundError,
        match=(
            f"Resource file for 'PydanticManagerTest' not found at: '{resource_path}'"
        ),
    ):
        test_manager.load()


def test_pydantic_resource_manager_save(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests saving a Pydantic resource that does not yet exist."""
    test_manager = PydanticManagerTest(fmu_dir)
    resource_model = PydanticResourceTest(foo="bar")

    test_manager.save(resource_model)

    assert test_manager.exists
    assert test_manager._cache == resource_model
    with open(test_manager.path, encoding="utf-8") as f:
        a_dict = json.loads(f.read())

    assert resource_model == PydanticResourceTest.model_validate(a_dict)


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

    test_manager = PydanticManagerTest(fmu_dir)
    with pytest.raises(PermissionError, match="Cannot write to .fmu directory"):
        test_manager.save(PydanticResourceTest(foo="bar"))

    with (
        patch("socket.gethostname", return_value="other-host"),
        patch("os.getpid", return_value=12345),
    ):
        lock.release()


def test_pydantic_resource_manager_load(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests loading a Pydantic resource."""
    test_manager = PydanticManagerTest(fmu_dir)
    test_resource = PydanticResourceTest(foo="bar")
    test_manager.save(test_resource)
    assert test_manager.load() == test_resource
    assert test_manager._cache == test_resource


def test_pydantic_resource_manager_load_force_true(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests loading a Pydantic resource with force=True."""
    test_manager = PydanticManagerTest(fmu_dir)
    test_resource = PydanticResourceTest(foo="bar")
    test_manager.save(test_resource)
    assert test_manager.load() == test_resource
    assert test_manager._cache == test_resource

    shadow_test_manager = PydanticManagerTest(fmu_dir)
    shadow_test_resource = PydanticResourceTest(foo="baz")
    shadow_test_manager.save(shadow_test_resource)

    assert shadow_test_manager.load() == shadow_test_resource
    assert shadow_test_manager._cache == shadow_test_resource

    assert test_manager.load() == test_resource
    assert test_manager._cache == test_resource

    assert test_manager.load(force=True) == shadow_test_resource
    assert test_manager._cache == shadow_test_resource


def test_pydantic_resource_manager_load_cache_false(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests loading a Pydantic resource with cache=False."""
    test_manager = PydanticManagerTest(fmu_dir)
    test_resource = PydanticResourceTest(foo="bar")
    test_manager.save(test_resource)

    shadow_test_manager = PydanticManagerTest(fmu_dir)
    assert shadow_test_manager.load(store_cache=False) == test_resource
    assert shadow_test_manager._cache is None

    assert shadow_test_manager.load(store_cache=True) == test_resource
    assert shadow_test_manager._cache == test_resource


def test_pydantic_resource_manager_load_force_true_cache_false(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests loading a Pydantic resource with force=True, cache=False."""
    test_manager = PydanticManagerTest(fmu_dir)
    test_resource = PydanticResourceTest(foo="bar")
    test_manager.save(test_resource)

    shadow_test_manager = PydanticManagerTest(fmu_dir)
    shadow_test_resource = PydanticResourceTest(foo="baz")
    shadow_test_manager.save(shadow_test_resource)

    assert test_manager.load(force=True, store_cache=False) == shadow_test_resource
    assert test_manager._cache is test_resource


def test_pydantic_resource_manager_loads_invalid_model(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests loading a Pydantic resource."""
    test_manager = PydanticManagerTest(fmu_dir)
    test_resource = PydanticResourceTest(foo="bar")
    test_manager.save(test_resource)

    test_resource_dict = test_resource.model_dump()
    test_resource_dict["foo"] = 0

    fmu_dir.write_text_file(test_manager.path, json.dumps(test_resource_dict))

    with pytest.raises(
        ValueError, match=r"Invalid content in resource file[\s\S]*input_value=0"
    ):
        test_manager.load(force=True)


def test_pydantic_resource_manager_save_does_not_cache_when_disabled(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Saving without cache enabled should not create cache artifacts."""
    test_manager = PydanticManagerTest(fmu_dir)
    original_default = test_manager.automatic_caching
    test_manager.automatic_caching = False
    cache_root = fmu_dir.path / "cache"
    try:
        if cache_root.exists():
            shutil.rmtree(cache_root)
        test_manager.save(PydanticResourceTest(foo="bar"))
    finally:
        test_manager.automatic_caching = original_default

    assert not cache_root.exists()


def test_pydantic_resource_manager_save_stores_revision_when_enabled(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Saving with cache enabled should persist a revision snapshot."""
    test_manager = PydanticManagerTest(fmu_dir)
    model = PydanticResourceTest(foo="bar")
    test_manager.save(model)

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
        test_manager = PydanticManagerTest(fmu_dir)
        test_manager.save(PydanticResourceTest(foo="one"))
        test_manager.save(PydanticResourceTest(foo="two"))
        test_manager.save(PydanticResourceTest(foo="three"))
        test_manager.save(PydanticResourceTest(foo="four"))
        test_manager.save(PydanticResourceTest(foo="five"))
        test_manager.save(PydanticResourceTest(foo="six"))
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


def test_pydantic_resource_manager_get_resource_diff(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests the happy path of getting a diff with another Pydantic resource."""
    test_manager = PydanticManagerTest(fmu_dir)
    test_manager.save(PydanticResourceTest(foo="current_value"))
    test_incoming_resource = PydanticResourceTest(foo="incoming_value")

    diff = test_manager.get_resource_diff(test_incoming_resource)

    assert len(diff) == 1
    assert diff[0][0] == "foo"
    assert diff[0][1] == "current_value"
    assert diff[0][2] == "incoming_value"


def test_pydantic_resource_manager_get_resource_diff_raises_when_other_type(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that a TypeError is raised when to diffing a different resource type."""
    test_manager = PydanticManagerTest(fmu_dir)
    test_manager.save(PydanticResourceTest(foo="current_value"))
    test_incoming_resource = MutablePydanticResourceTest(foo="incoming_value")

    with pytest.raises(
        TypeError,
        match=(
            "Resources to diff must be of the same type. Current resource is of type "
            "'PydanticResourceTest', incoming resource of type "
            "'MutablePydanticResourceTest'."
        ),
    ):
        test_manager.get_resource_diff(test_incoming_resource)


def test_pydantic_resource_manager_get_model_diff(fmu_dir: ProjectFMUDirectory) -> None:
    """Tests the happy path of getting a diff between two Pydantic models."""
    test_manager = PydanticManagerTest(fmu_dir)
    current_model = PydanticResourceTest(foo="current_value")
    incoming_model = PydanticResourceTest(foo="incoming_value")

    model_diff = test_manager.get_model_diff(current_model, incoming_model)

    assert len(model_diff) == 1
    assert model_diff[0][0] == "foo"
    assert model_diff[0][1] == "current_value"
    assert model_diff[0][2] == "incoming_value"


def test_pydantic_resource_manager_get_model_diff_raises_when_different_type(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """A ValueError should be raised for a diff between two different model types."""
    test_manager = PydanticManagerTest(fmu_dir)
    current_model = PydanticResourceTest(foo="current_value")
    incoming_model = MutablePydanticResourceTest(foo="incoming_value")

    with pytest.raises(
        ValueError,
        match=(
            "Models must be of the same type. Current model is of type "
            "'PydanticResourceTest', incoming model of type "
            "'MutablePydanticResourceTest'."
        ),
    ):
        test_manager.get_model_diff(current_model, incoming_model)


def test_pydantic_resource_manager_get_model_diff_ignore_fields(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that the expected fields are ignored when creating a diff."""

    class ExamplePydanticModel(BaseModel):
        data: str
        metadata: str
        created_at: AwareDatetime = datetime.now(UTC)
        created_by: str = "tester"

    test_manager = PydanticManagerTest(fmu_dir)
    current_model = ExamplePydanticModel(data="some_data", metadata="some_metadata")
    incoming_model = ExamplePydanticModel(
        data="some_newer_data", metadata="some_newer_metadata"
    )
    model_diff = test_manager.get_model_diff(current_model, incoming_model)

    exepected_length = 2
    assert len(model_diff) == exepected_length
    assert model_diff[0][0] == "data"
    assert model_diff[1][0] == "metadata"


def test_pydantic_resource_manager_get_diff_when_base_model_diff(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests getting a diff between two Pydantic models containing base models.

    Checks that a diff in a base model within the model is returned as expected.
    """

    class ExamplePydanticModel(BaseModel):
        data: str
        metadata: str
        name: str

    class ExampleNestedPydanticModel(BaseModel):
        parent: str
        child: ExamplePydanticModel

    test_manager = PydanticManagerTest(fmu_dir)
    current_model = ExampleNestedPydanticModel(
        parent="parent",
        child=ExamplePydanticModel(
            data="test_data", metadata="test_metadata", name="first"
        ),
    )
    incoming_model = ExampleNestedPydanticModel(
        parent="parent",
        child=ExamplePydanticModel(
            data="test_data", metadata="test_metadata_update", name="second"
        ),
    )
    model_diff = test_manager.get_model_diff(current_model, incoming_model)
    expected_length = 2
    assert len(model_diff) == expected_length
    assert model_diff[0] == ("child.metadata", "test_metadata", "test_metadata_update")
    assert model_diff[1] == ("child.name", "first", "second")


def test_pydantic_resource_manager_get_diff_when_list_diff(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests getting a diff between two Pydantic models containing list values.

    Checks that a diff in a list is returned as expected.
    """

    class ExamplePydanticModel(BaseModel):
        data: str
        name_list: list[str]

    test_manager = PydanticManagerTest(fmu_dir)
    current_list = ["item1", "item2", "item3"]
    current_model = ExamplePydanticModel(data="some_data", name_list=current_list)
    incoming_list = ["item4", "item5", "item3"]
    incoming_model = ExamplePydanticModel(data="some_data", name_list=incoming_list)

    model_diff = test_manager.get_model_diff(current_model, incoming_model)
    assert len(model_diff) == 1
    assert model_diff[0] == ("name_list", current_list, incoming_list)


def test_pydantic_resource_manager_get_diff_when_value_is_none(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests getting a diff between two Pydantic models containing None values.

    Checks that None values in any of the models are handled as expected.
    """

    class ExamplePydanticModel(BaseModel):
        data: str | None

    test_manager = PydanticManagerTest(fmu_dir)
    current_model = ExamplePydanticModel(data=None)
    incoming_model = ExamplePydanticModel(data="new_data")

    model_diff = test_manager.get_model_diff(current_model, incoming_model)
    assert model_diff == [("data", None, "new_data")]

    model_diff = test_manager.get_model_diff(incoming_model, current_model)
    assert model_diff == [("data", "new_data", None)]


def test_mutable_resource_manager_merge_other_resource(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests merging a Pydantic resource into the managers resource."""
    test_manager = MutablePydanticManagerTest(fmu_dir)
    test_manager.save(MutablePydanticResourceTest(foo="current_value"))
    test_incoming_resource = MutablePydanticResourceTest(foo="incoming_value")

    updated_resource = test_manager.merge_resource(test_incoming_resource)
    assert updated_resource == test_incoming_resource


def test_mutable_resource_manager_merge_resource_raises_when_other_type(
    fmu_dir: ProjectFMUDirectory,
) -> None:
    """Tests that a TypeError is raised when merging a different resource type."""
    test_manager = MutablePydanticManagerTest(fmu_dir)
    test_manager.save(MutablePydanticResourceTest(foo="current_value"))
    test_incoming_resource = PydanticResourceTest(foo="incoming_value")

    with pytest.raises(
        TypeError,
        match=(
            "Merging pydantic resource failed. The incoming resource must be of type "
            "'MutablePydanticResourceTest'. The provided model was of type "
            "'PydanticResourceTest'."
        ),
    ):
        test_manager.merge_resource(test_incoming_resource)
