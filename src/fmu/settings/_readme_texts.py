"""Shared README content for .fmu directories."""

from textwrap import dedent
from typing import Final

PROJECT_README_CONTENT: Final[str] = dedent(
    """\
    This directory contains static configuration data for your FMU project.

    You should *not* manually modify files within this directory. Doing so may
    result in erroneous behavior or erroneous data in your FMU project.

    Changes to data stored within this directory must happen through the FMU
    Settings application.

    Run `fmu settings` to do this.
    """
)

USER_README_CONTENT: Final[str] = dedent(
    """\
    This directory contains static data and configuration elements used by some
    components in FMU. It may also contains sensitive access tokens that should not be
    shared with others.

    You should *not* manually modify files within this directory. Doing so may
    result in erroneous behavior by some FMU components.

    Changes to data stored within this directory must happen through the FMU
    Settings application.

    Run `fmu settings` to do this.
    """
)
