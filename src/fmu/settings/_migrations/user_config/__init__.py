"""Migration function registry for user config resources."""

from fmu.settings._migrations.manager import MigrationFunction

USER_CONFIG_MIGRATIONS: dict[int, MigrationFunction] = {}

__all__ = ["USER_CONFIG_MIGRATIONS"]
