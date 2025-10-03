"""Tests for fmu.settings._global_config."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import yaml
from fmu.datamodels.fmu_results import fields
from fmu.datamodels.fmu_results.global_configuration import (
    GlobalConfiguration,
    StratigraphyElement,
)

from fmu.settings._global_config import (
    _find_global_config_file,
    _find_global_variables_file,
    find_global_config,
    load_global_configuration_if_present,
    validate_global_configuration_strictly,
)

STRICT_VALIDATION_IDENTIFIERS: list[tuple[str, bool]] = [
    ("Drogon", False),  # False = not valid, True = valid
    ("DROGON", False),
    ("drogon_2020", False),
    ("Dragon", True),
    ("TROLL", True),
]

STRICT_VALIDATION_UUIDS: list[tuple[UUID, bool]] = [
    (UUID("ad214d85-dac7-19da-e053-c918a4889309"), False),
    (UUID("ad214d85-8a1d-19da-e053-c918a4889310"), False),
    (UUID("00000000-0000-0000-0000-000000000000"), False),
    (uuid4(), True),
]

STRICT_VALIDATION_STRAT_COLS: list[tuple[str, bool]] = [
    ("TopVolantis", False),
    ("Valysar", False),
    ("Viking", True),
]


# Test validation of invalid content/values.


@pytest.mark.parametrize("name, valid", STRICT_VALIDATION_IDENTIFIERS)
def test_validate_global_config_strict_model(
    name: str,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'model'."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        model=fields.Model(name=name, revision=""),
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(ValueError, match=f"Invalid name in 'model': {name}"):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("name, valid", STRICT_VALIDATION_IDENTIFIERS)
def test_validate_global_config_strict_access(
    name: str,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'access'."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        asset=fields.Asset(name=name),
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(ValueError, match=f"Invalid name in 'access.asset': {name}"):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("uuid, valid", STRICT_VALIDATION_UUIDS)
def test_validate_global_config_strict_smda_country_uuid(
    uuid: UUID,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.country' uuids."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        country_items=[
            fields.CountryItem(identifier="bar", uuid=uuid),
            fields.CountryItem(identifier="foo", uuid=uuid4()),
        ],
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError, match=f"Invalid SMDA UUID in 'smda.country': {uuid}"
        ):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("identifier, valid", STRICT_VALIDATION_IDENTIFIERS)
def test_validate_global_config_strict_smda_discovery_identifier(
    identifier: str,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.discovery' identifiers."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        discovery_items=[
            fields.DiscoveryItem(short_identifier=identifier, uuid=uuid4()),
            fields.DiscoveryItem(short_identifier="foo", uuid=uuid4()),
        ],
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError,
            match=f"Invalid SMDA short identifier in 'smda.discovery': {identifier}",
        ):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("uuid, valid", STRICT_VALIDATION_UUIDS)
def test_validate_global_config_strict_smda_discovery_uuid(
    uuid: UUID,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.discovery' uuids."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        discovery_items=[
            fields.DiscoveryItem(short_identifier="bar", uuid=uuid),
            fields.DiscoveryItem(short_identifier="foo", uuid=uuid4()),
        ],
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError,
            match=f"Invalid SMDA UUID in 'smda.discovery': {uuid}",
        ):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("identifier, valid", STRICT_VALIDATION_IDENTIFIERS)
def test_validate_global_config_strict_smda_field_identifier(
    identifier: str,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.discovery' identifiers."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        field_items=[
            fields.FieldItem(identifier=identifier, uuid=uuid4()),
            fields.FieldItem(identifier="foo", uuid=uuid4()),
        ],
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError,
            match=f"Invalid SMDA identifier in 'smda.field': {identifier}",
        ):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("uuid, valid", STRICT_VALIDATION_UUIDS)
def test_validate_global_config_strict_smda_field_uuid(
    uuid: UUID,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.discovery' uuids."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        field_items=[
            fields.FieldItem(identifier="bar", uuid=uuid),
            fields.FieldItem(identifier="foo", uuid=uuid4()),
        ],
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError,
            match=f"Invalid SMDA UUID in 'smda.field': {uuid}",
        ):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("uuid, valid", STRICT_VALIDATION_UUIDS)
def test_validate_global_config_strict_coordinate_system(
    uuid: UUID,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.coordinate_system'."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        coordinate_system=fields.CoordinateSystem(identifier="", uuid=uuid),
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError, match=f"Invalid SMDA UUID in 'smda.coordinate_system': {uuid}"
        ):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("uuid, valid", STRICT_VALIDATION_UUIDS)
def test_validate_global_config_strict_stratigraphic_column_uuids(
    uuid: UUID,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.stratigraphic_column' uuid."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        stratigraphic_column=fields.StratigraphicColumn(identifier="", uuid=uuid),
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError,
            match=f"Invalid SMDA UUID in 'smda.stratigraphic_column': {uuid}",
        ):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("identifier, valid", STRICT_VALIDATION_IDENTIFIERS)
def test_validate_global_config_strict_stratigraphic_column_names(
    identifier: str,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.stratigraphic_column' identifiers."""
    cfg = generate_strict_valid_globalconfiguration(  # type: ignore
        stratigraphic_column=fields.StratigraphicColumn(
            identifier=identifier, uuid=uuid4()
        ),
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError,
            match=f"Invalid SMDA identifier in 'smda.stratigraphic_column': "
            f"{identifier}",
        ):
            validate_global_configuration_strictly(cfg)


@pytest.mark.parametrize("identifier, valid", STRICT_VALIDATION_STRAT_COLS)
def test_validate_global_config_strict_stratigraphy_names(
    identifier: str,
    valid: bool,
    generate_strict_valid_globalconfiguration: Callable[[], GlobalConfiguration],
) -> None:
    """Tests strict validation on 'smda.stratigraphic_column' identifiers."""
    cfg = generate_strict_valid_globalconfiguration()
    assert cfg.stratigraphy
    cfg.stratigraphy.root[identifier] = StratigraphyElement(
        name=identifier, stratigraphic=False
    )
    if valid:
        validate_global_configuration_strictly(cfg)  # Does not raise
    else:
        with pytest.raises(
            ValueError,
            match=f"Invalid stratigraphy name in 'smda.stratigraphy': {identifier}",
        ):
            validate_global_configuration_strictly(cfg)


# Test load_global_configuration_if_present


@pytest.mark.parametrize("fmu_load", [True, False])
def test_load_global_configuration_returns_none_if_invalid_yaml(
    fmu_load: bool, tmp_path: Path
) -> None:
    """Tests maybe_load returns None if an Exception is raised."""
    config_path = tmp_path / "global_config.yml"
    with open(config_path, "w") as f:
        f.write("foo=bar")

    assert load_global_configuration_if_present(config_path, fmu_load=fmu_load) is None


@pytest.mark.parametrize("fmu_load", [True, False])
def test_load_global_configuration_returns_none_if_invalid_config(
    fmu_load: bool,
    tmp_path: Path,
    global_variables_with_masterdata: dict[str, Any],
) -> None:
    """Tests maybe_load returns None if an Exception is raised."""
    config_path = tmp_path / "global_config.yml"
    del global_variables_with_masterdata["masterdata"]
    with open(config_path, "w") as f:
        yaml.safe_dump(global_variables_with_masterdata, f)

    assert load_global_configuration_if_present(config_path, fmu_load=fmu_load) is None


# Test finding global variables


def test_find_global_config_file_not_there(tmp_path: Path) -> None:
    """Tests finding the global config file if it is not present."""
    assert _find_global_config_file([]) is None
    assert _find_global_config_file([tmp_path]) is None
    assert _find_global_config_file([tmp_path / "dne"]) is None


def test_find_global_configs_file_malformed(tmp_path: Path) -> None:
    """Tests finding the global config file if it is malformed."""
    with open(tmp_path / "global_master_config.yml", "w") as f:
        f.write("foo: bar")
    assert _find_global_config_file([tmp_path]) is None


def test_find_global_config_file(fmuconfig_with_output: Path) -> None:
    """Tests finding the global variables file in fmuconfig."""
    tmp_path = fmuconfig_with_output
    some_dir = tmp_path / "some_dir"
    some_dir.mkdir()
    some_file = some_dir / "some_file"
    some_file.touch()
    does_not_exist = tmp_path / "bad"
    assert _find_global_config_file([does_not_exist, some_dir, some_file]) is None

    fmuconfig_input = fmuconfig_with_output / "fmuconfig/input"
    global_variables = fmuconfig_input / "global_master_config.yml"
    shutil.copy(global_variables, fmuconfig_input / "global_master_config_pred.yml")

    assert isinstance(
        _find_global_config_file(
            [does_not_exist, some_dir, some_file, fmuconfig_input]
        ),
        GlobalConfiguration,
    )


def test_find_global_variables_file_not_there(tmp_path: Path) -> None:
    """Tests finding the global variables file if it is not present."""
    assert _find_global_variables_file([]) is None
    assert _find_global_variables_file([tmp_path]) is None
    assert _find_global_variables_file([tmp_path / "dne"]) is None


def test_find_global_variables_file_malformed(tmp_path: Path) -> None:
    """Tests finding the global variables file if it is malformed."""
    with open(tmp_path / "global_variables.yml", "w") as f:
        f.write("foo: bar")
    assert _find_global_variables_file([tmp_path]) is None


def test_find_global_variables_file(fmuconfig_with_output: Path) -> None:
    """Tests finding the global variables file in fmuconfig."""
    tmp_path = fmuconfig_with_output
    some_dir = tmp_path / "some_dir"
    some_dir.mkdir()
    some_file = some_dir / "some_file"
    some_file.touch()
    does_not_exist = tmp_path / "bad"
    assert _find_global_variables_file([does_not_exist, some_dir, some_file]) is None

    assert isinstance(
        _find_global_variables_file(
            [
                does_not_exist,
                some_dir,
                some_file,
                fmuconfig_with_output / "fmuconfig/output",
            ]
        ),
        GlobalConfiguration,
    )


def test_find_global_config_does_not_exist(tmp_path: Path) -> None:
    """Tests that find_global_config returns None if no config exists."""
    assert find_global_config(tmp_path) is None
    assert find_global_config(tmp_path, strict=False) is None


def test_find_global_config_from_input_non_strict(
    fmuconfig_with_input: Path,
) -> None:
    """Tests finding a global config from the input dir."""
    tmp_path = fmuconfig_with_input
    cfg = find_global_config(tmp_path, strict=False)
    assert isinstance(cfg, GlobalConfiguration)

    # Validate all fields present
    assert cfg.access.asset.name == "Drogon"
    assert cfg.access.classification == "internal"
    assert cfg.masterdata.smda.country[0].identifier == "Norway"
    assert cfg.masterdata.smda.discovery[0].short_identifier == "DROGON"
    assert cfg.masterdata.smda.field[0].identifier == "DROGON"
    assert cfg.masterdata.smda.coordinate_system.identifier == "ST_WGS84_UTM37N_P32637"
    assert (
        cfg.masterdata.smda.stratigraphic_column.identifier
        == "DROGON_HAS_NO_STRATCOLUMN"
    )
    assert cfg.model.name == "Drogon"
    assert cfg.stratigraphy is not None
    assert cfg.stratigraphy["TopVolantis"].name == "VOLANTIS GP. Top"


def test_find_global_config_from_input_strict(
    fmuconfig_with_input: Path,
) -> None:
    """Tests finding a global config with 'Drogon' in it raises."""
    tmp_path = fmuconfig_with_input
    with pytest.raises(ValueError, match="Invalid name in 'model': Drogon"):
        find_global_config(tmp_path)


def test_find_global_config_extra_output_paths(
    fmuconfig_with_output: Path,
) -> None:
    """Tests finding global variables with extra output paths."""
    tmp_path = fmuconfig_with_output
    base_path = tmp_path / "some_dir"
    base_path.mkdir()

    cfg = find_global_config(
        base_path,
        extra_output_paths=[tmp_path / "fmuconfig/output/global_variables.yml"],
        strict=False,
    )
    assert isinstance(cfg, GlobalConfiguration)

    with pytest.raises(ValueError, match="Invalid name in 'model': Drogon"):
        find_global_config(
            base_path,
            extra_output_paths=[tmp_path / "fmuconfig/output/global_variables.yml"],
        )
    assert isinstance(cfg, GlobalConfiguration)


def test_find_global_config_extra_input_paths(
    fmuconfig_with_input: Path,
) -> None:
    """Tests finding global variables with extra input paths."""
    tmp_path = fmuconfig_with_input
    base_path = tmp_path / "some_dir"
    base_path.mkdir()

    cfg = find_global_config(
        base_path,
        extra_input_dirs=[tmp_path / "fmuconfig/input"],
        strict=False,
    )
    assert isinstance(cfg, GlobalConfiguration)

    with pytest.raises(ValueError, match="Invalid name in 'model': Drogon"):
        find_global_config(
            base_path,
            extra_input_dirs=[tmp_path / "fmuconfig/input"],
        )
    assert isinstance(cfg, GlobalConfiguration)
