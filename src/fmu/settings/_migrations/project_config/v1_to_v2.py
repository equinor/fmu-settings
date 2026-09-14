"""Convert absolute RMS project paths to relative paths."""

from pathlib import PurePosixPath
from typing import Any


def migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate project config to schema version two.

    Convert an absolute RMS path to a path relative to the FMU project root.
    For example, convert ``/path/to/revision/rms/model/drogon.rms15`` to
    ``rms/model/drogon.rms15``.
    """
    rms = data.get("rms")
    if rms is not None:
        path = PurePosixPath(rms["path"])
        if path.is_absolute():
            if path.parts[-3:-1] != ("rms", "model"):
                raise ValueError(
                    f"Cannot migrate RMS path '{path}'. "
                    "Expected an absolute path ending in 'rms/model/<project>'."
                )
            rms["path"] = str(PurePosixPath(*path.parts[-3:]))
    data["schema_version"] = 2
    return data
