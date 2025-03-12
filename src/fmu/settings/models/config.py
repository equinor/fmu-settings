"""The generic configuration file in a .fmu directory."""

from pydantic import AwareDatetime, BaseModel

from .types import VersionStr


class Config(BaseModel):
    """The configuration file in a .fmu directory.

    Stored as config.json.
    """

    version: VersionStr
    created_at: AwareDatetime
    created_by: str
