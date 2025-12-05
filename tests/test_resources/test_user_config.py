"""Tests specific to the user configuration.

Because the user config and the project config share the same base class a great deal of
the functionality is already tested in test_project_config.py. This test module is more
sparse to handle things specific to the user configuration.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from fmu.settings._fmu_dir import UserFMUDirectory
from fmu.settings.models.user_config import UserConfig


def test_set_smda_subscription_key_validates(user_fmu_dir: UserFMUDirectory) -> None:
    """Tests that setting a subscription key is validated by Pydantic."""
    config = user_fmu_dir.config.load()
    assert config.user_api_keys.smda_subscription is None
    with pytest.raises(ValueError, match="Invalid value set"):
        user_fmu_dir.set_config_value("user_api_keys.smda_subscription", 123)
    assert config.user_api_keys.smda_subscription is None

    user_fmu_dir.set_config_value("user_api_keys.smda_subscription", "secret")

    config = user_fmu_dir.config.load()
    assert config.user_api_keys.smda_subscription is not None
    assert config.user_api_keys.smda_subscription.get_secret_value() == "secret"

    user_fmu_dir.set_config_value("user_api_keys.smda_subscription", None)
    config = user_fmu_dir.config.load()


def test_set_smda_subscription_key_writes_to_disk(
    user_fmu_dir: UserFMUDirectory,
) -> None:
    """Tests that setting a subscription key updates to disk."""
    user_fmu_dir.set_config_value("user_api_keys.smda_subscription", "secret")
    config = user_fmu_dir.config.load()
    assert config.user_api_keys.smda_subscription is not None
    assert config.user_api_keys.smda_subscription.get_secret_value() == "secret"
    assert config.user_api_keys.smda_subscription == SecretStr("secret")
    assert user_fmu_dir.get_config_value(
        "user_api_keys.smda_subscription"
    ) == SecretStr("secret")
    assert (
        user_fmu_dir.get_config_value(
            "user_api_keys.smda_subscription"
        ).get_secret_value()
        == "secret"
    )

    with open(user_fmu_dir.config.path, encoding="utf-8") as f:
        config_dict = json.loads(f.read())
    assert config_dict["user_api_keys"]["smda_subscription"] == "secret"


def test_obfuscate_secrets(user_fmu_dir: UserFMUDirectory) -> None:
    """Tests the obfuscate_secrets() method on the UserConfig model."""
    user_fmu_dir.set_config_value("user_api_keys.smda_subscription", "secret")
    config = user_fmu_dir.config.load()
    assert config.user_api_keys.smda_subscription is not None
    assert config.user_api_keys.smda_subscription.get_secret_value() == "secret"
    assert config.user_api_keys.smda_subscription == SecretStr("secret")

    config_dump = config.model_dump()
    assert config_dump["user_api_keys"]["smda_subscription"] == SecretStr("secret")
    config_json = config.model_dump_json()
    assert '{"smda_subscription":"secret"}' in config_json

    secret_config = config.obfuscate_secrets()
    secret_config_dump = secret_config.model_dump()
    assert secret_config_dump["user_api_keys"]["smda_subscription"] == SecretStr(
        "**********"
    )
    secret_config_json = secret_config.model_dump_json()
    assert '{"smda_subscription":"**********"}' in secret_config_json


def test_user_config_reset_has_none_last_modified_at() -> None:
    """Tests that reset() creates a user config with None for last_modified_at."""
    config = UserConfig.reset()

    assert config.last_modified_at is None
    assert config.created_at is not None


def test_user_config_last_modified_at_set_on_save(
    user_fmu_dir: UserFMUDirectory,
) -> None:
    """Tests that last_modified_at is set when saving user config."""
    user_fmu_dir.config.set("cache_max_revisions", 10)

    updated_config = user_fmu_dir.config.load()
    assert updated_config.last_modified_at is not None

    now = datetime.now(UTC)
    one_min_ago = now - timedelta(minutes=1)
    assert one_min_ago <= updated_config.last_modified_at <= now
