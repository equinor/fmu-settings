"""The model for config.json."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Self

import annotated_types
from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    SecretStr,
    field_serializer,
    field_validator,
)

from fmu.settings import __version__
from fmu.settings.types import ResettableBaseModel, VersionStr  # noqa: TC001

RecentProjectDirectories = Annotated[list[Path], annotated_types.Len(0, 5)]


class UserAPIKeys(BaseModel):
    """Known API keys stored in a user config."""

    smda_subscription: SecretStr | None = None

    @field_serializer("smda_subscription", when_used="json")
    def dump_secret(self, v: SecretStr | None) -> str | None:
        """Write the secret string value when serializing to json."""
        if v is None:
            return None
        return v.get_secret_value()


class UserConfig(ResettableBaseModel):
    """The configuration file in a $HOME/.fmu directory.

    Stored as config.json.
    """

    version: VersionStr
    created_at: AwareDatetime
    cache_max_revisions: int = Field(default=5, ge=5)
    user_api_keys: UserAPIKeys
    recent_project_directories: RecentProjectDirectories

    @classmethod
    def reset(cls: type[Self]) -> Self:
        """Resets the model to an initial state."""
        return cls(
            version=__version__,
            created_at=datetime.now(UTC),
            cache_max_revisions=5,
            user_api_keys=UserAPIKeys(),
            recent_project_directories=[],
        )

    @field_validator("recent_project_directories", mode="before")
    @classmethod
    def ensure_unique(cls, recent_projects: list[Path]) -> list[Path]:
        """Ensures that recent_project_directories contains unique entries."""
        if len(recent_projects) != len(set(recent_projects)):
            raise ValueError("recent_project_directories must contain unique entries")
        return recent_projects

    def obfuscate_secrets(self: Self) -> Self:
        """Returns a copy of the model with obfuscated secrets.

        If an API Key is:

            key: SecretStr = SecretStr("secret")

        we may want to serialize it to JSON as:

            {key:"********"}

        so that we do not serialize the actual value of the secret when, for example,
        returning the user configuration from an API.
        """
        config_dict = self.model_dump()
        # Overwrite secret keys with obfuscated keys
        for k, v in config_dict["user_api_keys"].items():
            if v is not None:
                # Convert SecretStr("*********") to "*********"
                config_dict["user_api_keys"][k] = str(v)
        return self.model_validate(config_dict)
