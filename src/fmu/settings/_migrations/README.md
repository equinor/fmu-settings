# Schema migration guide

Use this guide when a stored `.fmu` resource needs a new schema version.

The supported resources and their migration registries are:

- `ProjectConfig`: `project_config/`
- `UserConfig`: `user_config/`
- `InternalMappings`: `mappings/`

## Decide whether to change the schema version

Change the schema version when existing stored data needs a conversion before it
can be used by the current model.

### Changes that need a migration

Renaming a stored field needs a migration. For example, changing
`cache_max_revisions` to `max_cache_revisions` changes the JSON object from:

```json
{
  "schema_version": 1,
  "cache_max_revisions": 5
}
```

to:

```json
{
  "schema_version": 2,
  "max_cache_revisions": 5
}
```

Without a migration, the current model cannot recover the value stored under the
old field name.

Other changes that need a migration include:

- Removing a stored field when its value must be moved or preserved elsewhere.
- Making an optional field required and calculating its value from old data.
- Changing a field from one type to another, such as a string to a list of strings.
- Moving flat fields into a nested model.
- Changing the meaning of a value when old data must be converted to keep its
  original meaning.

### Changes that do not need a migration

Adding an optional field with a safe default does not normally need a migration.
For example:

```python
class ProjectConfig(ResettableBaseModel):
    schema_version: Literal[1] = 1
    description: str | None = None
```

An existing version 1 file without `description` still validates. Pydantic supplies
`None`, so the schema version can remain 1.

Other changes that do not normally need a migration include:

- Making validation more permissive.
- Changing a model method that does not change stored data.
- Changing documentation or field descriptions.
- Adding a computed property that is not stored.

Old stored data must still produce the correct current model when no migration is
added. If the old data needs conversion or its meaning would change, add a schema
version and migration.

## Schema version contract

Each migratable model declares one positive integer schema version. The literal and
default values must match:

```python
schema_version: Literal[2] = 2
```

Migration functions are forward-only. Each function advances the data by exactly
one version:

```text
1 -> 2 -> 3
```

Do not skip a version. Data without a `schema_version` field is treated as schema
version 1.

## Add a migration

The following example changes the current `ProjectConfig` from schema version 1 to
2 and renames `cache_max_revisions` to `max_cache_revisions`.

### 1. Update the current model

Edit the existing model in `models/project_config.py`. Do not create a second
`ProjectConfig` class. The `...` lines below represent all unchanged fields in the
current model, such as `version`, `created_at`, `created_by`, `masterdata`, and
`rms`. Only the schema version and the renamed field change in this example:

```python
class ProjectConfig(ResettableBaseModel):
    """The configuration file in a .fmu directory."""

    schema_version: Literal[2] = 2
    # ... unchanged fields ...
    max_cache_revisions: int = Field(default=5, ge=5)
    # ... unchanged fields ...

    @classmethod
    def reset(cls: type[Self]) -> Self:
        """Reset the configuration to its defaults."""
        return cls(
            # ... unchanged defaults ...
            max_cache_revisions=5,
            # ... unchanged defaults ...
        )
```

Search the source code and tests for the old field name. Update attribute access
such as `config.cache_max_revisions`, string keys such as
`set_config_value("cache_max_revisions", ...)`, API models, and test input
dictionaries. Any code that reads or writes this field must use the new name.

### 2. Add one migration function

Create `project_config/v1_to_v2.py`:

```python
from typing import Any


def migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate project config data from schema version 1 to 2."""
    data["max_cache_revisions"] = data.pop("cache_max_revisions", 5)
    data["schema_version"] = 2
    return data
```

The migration manager gives each migration function a deep copy of the loaded
data. A migration function can therefore modify its input without changing the
original data.

The returned data must:

- Preserve all relevant stored values.
- Set `schema_version` to the next version.
- Be valid input for the next migration or the current model.

### 3. Register the migration

Update `project_config/__init__.py`:

```python
from fmu.settings._migrations.manager import Migration

from .v1_to_v2 import migrate_v1_to_v2

PROJECT_CONFIG_MIGRATIONS: dict[int, Migration] = {
    1: migrate_v1_to_v2,
}
```

The registry key is the source version. Key `1` registers the migration from
version 1 to version 2.

Keep every migration when later versions are added:

```python
PROJECT_CONFIG_MIGRATIONS: dict[int, Migration] = {
    1: migrate_v1_to_v2,
    2: migrate_v2_to_v3,
}
```

## Test the migration

When you add a migration:

- Keep `test_migration_manager.py` and the generic resource tests unchanged unless
  the framework behavior changes.
- In `test_resource_migration.py`, update the affected resource tests that assert
  its version, migration registry, or previous version data.
- Add resource-specific tests under `tests/test_migrations/`. For example, a
  `ProjectConfig` migration can use `test_project_config_migration.py`.

The resource-specific tests must cover conversion, load, save, cache restore, and
invalid data. Update the complete current version fixture used by
`tests/test_resources/test_migratable_models_up_to_date.py`. Keep the previous
version input with the resource-specific migration tests.

Run the relevant checks:

```text
uv run pytest tests/test_migrations
uv run pytest tests/test_resources/test_migratable_models_up_to_date.py
uv run ruff check
uv run ruff format --check
uv run mypy src tests
```

## Runtime behavior

Migration is automatic during normal use:

1. The resource manager reads old data.
2. The migration manager converts it in memory.
3. The resource manager returns the current validated model.
4. The stored file remains unchanged until a save occurs.

On the first save:

1. The write lock is checked.
2. The original stored data is added to the normal cache revisions.
3. The current model is written with the new schema version.
4. The new stored data is added to the normal cache revisions.

Loading a resource does not create a changelog entry. A later user update or
restore uses the existing changelog behavior.

When an old cache revision is restored, it is migrated before it is written. The
resource file therefore uses the current schema after the restore.

Migrations are forward-only. After current-schema data is saved, an older
`fmu-settings` release can reject it as newer than its supported schema.

## Release checklist for an `fmu-settings` schema version

Use this checklist when releasing an `fmu-settings` package that contains a new
stored schema version. First prepare and publish `fmu-settings`. Then update the
downstream applications so that users receive the new package.

### 1. Prepare the `fmu-settings` package

- Confirm that the schema change needs a migration.
- Increase the model schema version by one.
- Add and register the migration from the previous version.
- Update `reset()` if it constructs or supplies a default for the changed field.
- Update test fixture dictionaries so that current-model fixtures use the new field
  and current schema version.
- Update Python attribute access, dot-notation string keys, API code, and other
  callers that use the changed field.
- Test loading, saving, caching, and restoring previous-version data.
- Run the full `fmu-settings` checks.

### 2. Publish the `fmu-settings` package

Publish a new GitHub release for `fmu-settings`. The publish workflow builds the
package and uploads it to PyPI.

### 3. Release `fmu-settings-api`

1. Set the minimum `fmu-settings` dependency in `fmu-settings-api` to the newly
   released version.
2. Update the API lockfile and run the API tests.
3. Publish a new `fmu-settings-api` release.

If the schema change affects fields exposed by the API, update and verify the
OpenAPI schema. Then regenerate and release the GUI client.

### 4. Release `fmu-settings-cli`

1. Set the minimum `fmu-settings-api` dependency in `fmu-settings-cli` to the newly
   released API version.
2. Also set the CLI's direct `fmu-settings` dependency to the new version.
3. Update the CLI lockfile and run the CLI tests.
4. Publish a new `fmu-settings-cli` release.

This release order keeps the schema implementation, API runtime, and CLI
distribution on compatible versions.
