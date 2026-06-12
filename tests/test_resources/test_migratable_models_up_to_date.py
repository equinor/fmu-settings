"""Tests for the migratable data models."""

import copy
from enum import Enum
from typing import Any

from pydantic import BaseModel, RootModel

from fmu.settings.models.mappings import InternalMappings
from fmu.settings.models.project_config import ProjectConfig
from fmu.settings.models.user_config import UserConfig


def _all_recursive_fields_set(obj: BaseModel) -> bool:
    """Checks whether all recursive fields in a given BaseModel object are set.

    Check that all recursive fields for a given BaseModel are set to a
    value different to None or empty list.
    """
    if isinstance(obj, BaseModel):
        if isinstance(obj, RootModel):
            return _all_recursive_fields_set(obj.root)
        return all(_all_recursive_fields_set(value) for value in obj.__dict__.values())
    if isinstance(obj, list):
        if len(obj) == 0:
            return False
        return all(_all_recursive_fields_set(value) for value in obj)
    if hasattr(obj, "__dict__"):
        if isinstance(obj, Enum):
            return obj is not None
        return all(_all_recursive_fields_set(value) for value in obj.__dict__.values())
    return obj is not None


def test_project_config_model_needs_migration(
    mocked_project_config_with_all_fields: dict[str, Any],
) -> None:
    """Checks that the project config model does not need migration.

    Check that the current state of the project config model has not changed
    and needs a new version and migration script.

    The check is performed in two steps:
    1. Validate that the mocked project config file validates against the current model
    2. Assert that all optional fields are set to assure the full model is validated

    If step 1 fails:
        This indicates that the ProjectConfig model has been updated. This requires
        a bump in the ProjectConfig version from n to n+1, in addition to a new
        migration script, defining how to migrate from version n to n+1. The mocked
        project config file should be updated accordingly.
    If step 2 fails:
        This indicates that the mocked project config file being used does not have all
        optional fields set. This is needed in order to get a complete check.
    """
    assert set(mocked_project_config_with_all_fields) == set(ProjectConfig.model_fields)
    project_config = ProjectConfig.model_validate(mocked_project_config_with_all_fields)
    assert _all_recursive_fields_set(project_config)


def test_user_config_model_needs_migration(
    mocked_user_config_with_all_fields: dict[str, Any],
) -> None:
    """Checks that the user config model does not need migration.

    Check that the current state of the user config model has not changed
    and needs a new version and migration script.

    The check is performed in two steps:
    1. Validate that the mocked user config file validates against the current model
    2. Assert that all optional fields are set to assure the full model is validated

    If step 1 fails:
        This indicates that the UserConfig model has been updated. This requires
        a bump in the UserConfig version from n to n+1, in addition to a new
        migration script, defining how to migrate from version n to n+1. The mocked
        user config file should be updated accordingly.
    If step 2 fails:
        This indicates that the mocked user config file being used does not have all
        optional fields set. This is needed in order to get a complete check.
    """
    assert set(mocked_user_config_with_all_fields) == set(UserConfig.model_fields)
    user_config = UserConfig.model_validate(mocked_user_config_with_all_fields)
    assert _all_recursive_fields_set(user_config)


def test_internal_mappings_model_needs_migration(
    mocked_internal_mappings_with_all_fields: dict[str, Any],
) -> None:
    """Checks that the internal mappings model does not need migration.

    Check that the current state of the internal mappings model has not changed
    and needs a new version and migration script.

    The check is performed in two steps:
    1. Validate that the mocked mappings file validates against the current model
    2. Assert that all optional fields are set to assure the full model is validated

    If step 1 fails:
        This indicates that the InternalMappings model has been updated. This requires
        a bump in the InternalMappings version from n to n+1, in addition to a new
        migration script, defining how to migrate from version n to n+1. The mocked
        mappings file should be updated accordingly.
    If step 2 fails:
        This indicates that the mocked mappings file being used does not have all
        optional fields set. This is needed in order to get a complete check.
    """
    assert set(mocked_internal_mappings_with_all_fields) == set(
        InternalMappings.model_fields
    )
    mappings = InternalMappings.model_validate(mocked_internal_mappings_with_all_fields)
    assert _all_recursive_fields_set(mappings)


def test_all_recursive_fields_set_returns_false_when_field_is_none(
    mocked_project_config_with_all_fields: dict[str, Any],
) -> None:
    """Verify that a data object containing a None value is flagged correctly.

    Tests that the _all_recursive_fields_set method works as intended and returns
    False when a value in the data object is set to None.
    """
    project_config_dict_no_masterdata = copy.deepcopy(
        mocked_project_config_with_all_fields
    )
    project_config_dict_no_masterdata["masterdata"] = None
    project_config_no_masterdata = ProjectConfig.model_validate(
        project_config_dict_no_masterdata
    )
    assert _all_recursive_fields_set(project_config_no_masterdata) is False

    project_config_dict_no_model_description = copy.deepcopy(
        mocked_project_config_with_all_fields
    )
    project_config_dict_no_model_description["model"]["description"] = None
    project_config_no_model_description = ProjectConfig.model_validate(
        project_config_dict_no_model_description
    )
    assert _all_recursive_fields_set(project_config_no_model_description) is False


def test_all_recursive_fields_set_returns_false_when_empty_list_value(
    mocked_project_config_with_all_fields: dict[str, Any],
    mocked_internal_mappings_with_all_fields: dict[str, Any],
) -> None:
    """Verify that a data object containing an empty list value is flagged correctly.

    Tests that the _all_recursive_fields_set method works as intended and returns
    False when a value in the data object is an empty list.
    """
    project_config_dict_empty_discovery_list = copy.deepcopy(
        mocked_project_config_with_all_fields
    )
    project_config_dict_empty_discovery_list["masterdata"]["smda"]["discovery"] = []
    project_config_empty_country_list = ProjectConfig.model_validate(
        project_config_dict_empty_discovery_list
    )
    assert _all_recursive_fields_set(project_config_empty_country_list) is False

    mappings_dict_empty_wellbore_list = copy.deepcopy(
        mocked_internal_mappings_with_all_fields
    )
    mappings_dict_empty_wellbore_list["wellbore"] = []
    mappings_empty_wellbore_list = InternalMappings.model_validate(
        mappings_dict_empty_wellbore_list
    )
    assert _all_recursive_fields_set(mappings_empty_wellbore_list) is False
