"""Type annotations used in Pydantic models."""

from __future__ import annotations

from typing import Annotated, Self, TypeAlias

from pydantic import BaseModel, Field

VersionStr: TypeAlias = Annotated[
    str, Field(pattern=r"(\d+(\.\d+){0,2}|\d+\.\d+\.[a-z0-9]+\+[a-z0-9.]+)")
]


class ResettableBaseModel(BaseModel):
    """A Pydantic BaseModel that implements reset()."""

    @classmethod
    def reset(cls) -> Self:
        """Resets the model to an initial state."""
        raise NotImplementedError
