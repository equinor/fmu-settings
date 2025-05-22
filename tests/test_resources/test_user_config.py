"""Tests specific to the user configuration.

Because the user config and the project config share the same base class a great deal of
the functionality is already tested in test_project_config.py. This test module is more
sparse to handle things specific to the user configuration.
"""

import json

import pytest
from pydantic import SecretStr

from fmu.settings._fmu_dir import UserFMUDirectory


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
