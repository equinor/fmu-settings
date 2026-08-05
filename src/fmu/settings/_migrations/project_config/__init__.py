"""Migration function registry for project config resources."""

from fmu.settings._migrations.manager import MigrationFunction

PROJECT_CONFIG_MIGRATIONS: dict[int, MigrationFunction] = {}

__all__ = ["PROJECT_CONFIG_MIGRATIONS"]
