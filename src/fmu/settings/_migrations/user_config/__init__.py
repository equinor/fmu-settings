"""Migration registry for user config resources."""

from fmu.settings._migrations.manager import Migration

USER_CONFIG_MIGRATIONS: dict[int, Migration] = {}

__all__ = ["USER_CONFIG_MIGRATIONS"]
