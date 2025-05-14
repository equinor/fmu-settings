"""The model for config.json."""

import getpass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID  # noqa TC003

from pydantic import AwareDatetime, BaseModel, Field

from fmu.settings import __version__
from fmu.settings.types import ResettableBaseModel, VersionStr  # noqa TC001

from .smda import Smda


class Masterdata(BaseModel):
    """The ``masterdata`` block contains information related to masterdata.

    Currently, SMDA holds the masterdata.
    """

    smda: Smda | None = Field(default=None)
    """Block containing SMDA-related attributes. See :class:`Smda`."""


class ProjectConfig(ResettableBaseModel):
    """The configuration file in a .fmu directory.

    Stored as config.json.
    """

    version: VersionStr
    created_at: AwareDatetime
    created_by: str
    masterdata: Masterdata

    @classmethod
    def reset(cls: type[Self]) -> Self:
        """Resets the configuration to defaults.

        Returns:
            The new default Config object
        """
        return cls(
            version=__version__,
            created_at=datetime.now(UTC),
            created_by=getpass.getuser(),
            masterdata=Masterdata(),
        )
