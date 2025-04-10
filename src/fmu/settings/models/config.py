"""The model for config.json."""

from uuid import UUID  # noqa TC003

from pydantic import AwareDatetime, BaseModel, Field

from fmu.settings.types import VersionStr  # noqa TC001
from .smda import Smda


class Masterdata(BaseModel):
    """The ``masterdata`` block contains information related to masterdata.

    Currently, SMDA holds the masterdata.
    """

    smda: Smda | None = Field(default=None)
    """Block containing SMDA-related attributes. See :class:`Smda`."""


class Config(BaseModel):
    """The configuration file in a .fmu directory.

    Stored as config.json.
    """

    version: VersionStr
    created_at: AwareDatetime
    created_by: str
    masterdata: Masterdata
