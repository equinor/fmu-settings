"""Migration function registry for mappings resources."""

from fmu.settings._migrations.manager import MigrationFunction

MAPPINGS_MIGRATIONS: dict[int, MigrationFunction] = {}

__all__ = ["MAPPINGS_MIGRATIONS"]
