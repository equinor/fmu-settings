"""Migration function registry for project config resources."""

from fmu.settings._migrations.manager import MigrationFunction

from .v1_to_v2 import migrate_v1_to_v2

PROJECT_CONFIG_MIGRATIONS: dict[int, MigrationFunction] = {1: migrate_v1_to_v2}

__all__ = ["PROJECT_CONFIG_MIGRATIONS"]
