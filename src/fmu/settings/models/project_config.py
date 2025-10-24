"""The model for config.json."""

import getpass
from datetime import UTC, datetime
from typing import Self

from pydantic import AwareDatetime, Field

from fmu.datamodels.fmu_results.fields import Access, Masterdata, Model
from fmu.settings import __version__
from fmu.settings.types import ResettableBaseModel, VersionStr  # noqa: TC001


class ProjectConfig(ResettableBaseModel):
    """The configuration file in a .fmu directory.

    Stored as config.json.
    """

    version: VersionStr
    created_at: AwareDatetime
    created_by: str
    masterdata: Masterdata | None = Field(default=None)
    model: Model | None = Field(default=None)
    access: Access | None = Field(default=None)
    cache_max_revisions: int = Field(default=5, ge=5)

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
            masterdata=None,
            model=None,
            access=None,
            cache_max_revisions=5,
        )
