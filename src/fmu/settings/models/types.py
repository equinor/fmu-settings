"""Type annotations used in Pydantic models."""

from typing import Annotated, TypeAlias

from pydantic import Field

VersionStr: TypeAlias = Annotated[
    str, Field(pattern=r"(\d+(\.\d+){0,2}|\d+\.\d+\.[a-z0-9]+\+[a-z0-9.]+)")
]
