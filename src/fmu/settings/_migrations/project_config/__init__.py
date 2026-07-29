"""Migration registry for project config resources."""

from fmu.settings._migrations.manager import Migration

PROJECT_CONFIG_MIGRATIONS: dict[int, Migration] = {}

__all__ = ["PROJECT_CONFIG_MIGRATIONS"]
