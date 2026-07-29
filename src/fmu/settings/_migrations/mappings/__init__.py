"""Migration registry for mappings resources."""

from fmu.settings._migrations.manager import Migration

MAPPINGS_MIGRATIONS: dict[int, Migration] = {}

__all__ = ["MAPPINGS_MIGRATIONS"]
