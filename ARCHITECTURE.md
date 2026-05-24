# Architecture

This page describes the architecture owned by this repository and the high-level relationship between `fmu-settings` and the surrounding FMU Settings repositories.

`fmu-settings` is the behavioral core. It knows what a project `.fmu/` directory is and how to lock, diff, cache, restore, and validate its managed resources.

## Ecosystem Overview

```mermaid
flowchart LR
    CLI["fmu-settings-cli\nTyper launcher"]
    API["fmu-settings-api\nFastAPI backend"]
    GUI["fmu-settings-gui\nReact SPA + Python static host"]
    LIB["fmu-settings\nCore .fmu library"]
    MODELS["fmu-datamodels\nShared Pydantic domain models"]

    CLI -->|starts API and GUI processes\ncreates bootstrap token| API
    CLI -->|starts static GUI host\nopens browser URL| GUI
    CLI -->|uses init/find/sync/copy helpers| LIB
    CLI -->|loads global configuration models| MODELS

    GUI -->|generated OpenAPI client\nwith cookie session| API

    API -->|reads/writes .fmu resources\nlock/cache/changelog/session flows| LIB
    API -->|reuses typed domain models\nfor masterdata, mappings, RMS payloads| MODELS

    LIB -->|embeds masterdata, access, model,\nstratigraphy and mapping schemas| MODELS
```

The dependency chain is intentionally layered:

- [`fmu-settings`](https://github.com/equinor/fmu-settings) owns `.fmu/` directory behavior and core resource workflows.
- [`fmu-datamodels`](https://github.com/equinor/fmu-datamodels) provides the shared vocabulary for masterdata, access, global configuration, and mappings.
- [`fmu-settings-api`](https://github.com/equinor/fmu-settings-api) wraps the core library in a session-oriented application layer.
- [`fmu-settings-gui`](https://github.com/equinor/fmu-settings-gui) talks to the API and should not edit `.fmu/` files directly.
- [`fmu-settings-cli`](https://github.com/equinor/fmu-settings-cli) is the local orchestrator for bootstrapping user state, launching the API and GUI, and running utility commands.

## Core Library

```mermaid
classDiagram
    class FMUDirectoryBase {
        +base_path: Path
        +path: Path
        +config
        +cache: CacheManager
        +get_config_value(key, default)
        +set_config_value(key, value)
        +update_config(updates)
        +read_text_file(relative_path)
        +write_text_file(relative_path, content)
        +list_restorable_files()
        +restore()
    }

    class ProjectFMUDirectory {
        +changelog: ChangelogManager
        +mappings: MappingsManager
        +find_rms_projects()
        +get_dir_diff(new_fmu_dir)
        +sync_dir(new_fmu_dir)
        +restore_from_cache(relative_path, revision_id)
        +get_cache_content(relative_path, revision_id)
    }

    class UserFMUDirectory

    class CacheManager
    class LockManager {
        +acquire()
        +ensure_can_write()
        +refresh()
        +release()
        +is_acquired()
    }

    class PydanticResourceManager~PydanticResource~ {
        +load(force, store_cache)
        +save(model)
        +get_resource_diff(incoming_resource)
        +get_structured_model_diff(current_model, incoming_model)
    }

    class MutablePydanticResourceManager~MutablePydanticResource~ {
        +get(key, default)
        +set(key, value)
        +update(updates)
        +reset()
        +merge_changes(changes)
    }

    class ProjectConfigManager {
        +relative_path = config.json
        +save(model)
        +set(key, value)
        +update(updates)
    }

    class UserConfigManager {
        +relative_path = config.json
        +save(model)
    }

    class MappingsManager {
        +relative_path = mappings.json
        +update_stratigraphy_mappings(...)
        +update_wellbore_mappings(...)
        +read_rms_eclipse_csv(...)
        +write_rms_eclipse_csv(...)
    }

    class ChangelogManager
    class LogManager~Log~ {
        +add_log_entry(log_entry)
        +filter_log(filter)
    }
    class UserSessionLogManager

    FMUDirectoryBase <|-- ProjectFMUDirectory
    FMUDirectoryBase <|-- UserFMUDirectory

    PydanticResourceManager <|-- MutablePydanticResourceManager
    MutablePydanticResourceManager <|-- ProjectConfigManager
    MutablePydanticResourceManager <|-- UserConfigManager
    PydanticResourceManager <|-- LockManager
    PydanticResourceManager <|-- MappingsManager
    PydanticResourceManager <|-- LogManager
    LogManager <|-- UserSessionLogManager

    FMUDirectoryBase *-- LockManager
    FMUDirectoryBase *-- CacheManager
    ProjectFMUDirectory *-- ProjectConfigManager
    ProjectFMUDirectory *-- ChangelogManager
    ProjectFMUDirectory *-- MappingsManager
    UserFMUDirectory *-- UserConfigManager
```

The main library split is:

- `FMUDirectoryBase` is the filesystem-centered abstraction. It owns the `.fmu` path, lock manager, cache manager, and generic read/write helpers.
- `ProjectFMUDirectory` and `UserFMUDirectory` specialize the base class for project-local `.fmu/` directories and `$HOME/.fmu/`.
- `PydanticResourceManager` is the generic resource engine for loading, saving, diffing, and caching JSON-backed Pydantic models.
- `MutablePydanticResourceManager` adds dot-notation `get`, `set`, `update`, `reset`, and merge behavior for editable resources.
- `ProjectConfigManager`, `UserConfigManager`, `MappingsManager`, and `LogManager` bind specific Pydantic models to managed files inside `.fmu/`.
- Directory objects compose the correct managers and delegate resource operations to them.

## Runtime Flow

The full runtime spans multiple repositories, but this repository owns the `.fmu/` directory operations used by the API and CLI.

When a user runs `fmu settings`, the CLI starts a local application stack around this library:

1. The CLI ensures the user-level `.fmu/` directory exists, creating `$HOME/.fmu/` through `init_user_fmu_directory()` when needed.
2. It creates a short-lived bootstrap token used only to authenticate the browser session startup.
3. It starts the API process and gives it the bootstrap token and runtime settings.
4. It starts the GUI static-file host.
5. It opens the browser on the local GUI URL with the bootstrap token in the URL fragment.
6. The React app reads the token from the fragment, stores it in browser session storage, and exchanges it for an API session.
7. The API verifies the bootstrap token, ensures user settings are available, creates or renews a server-side session, and sets an HttpOnly session cookie.
8. If the command was launched from inside an initialized FMU project, the API locates the nearest project `.fmu/` directory and tries to acquire its lock.
9. After session setup, the GUI talks to the API with the session cookie, and the API uses `ProjectFMUDirectory` and `UserFMUDirectory` to read and write managed resources.

```mermaid
sequenceDiagram
    participant User
    participant CLI as fmu-settings-cli
    participant GUIHost as GUI static host
    participant Browser
    participant SPA as React SPA
    participant API as fmu-settings-api
    participant Session as SessionManager
    participant UserFMU as UserFMUDirectory
    participant ProjectFMU as ProjectFMUDirectory

    User->>CLI: run `fmu settings`
    CLI->>UserFMU: init_user_fmu_directory() if needed
    CLI->>CLI: generate bootstrap auth token
    CLI->>API: start local API process with token
    CLI->>GUIHost: start local GUI static-file host
    CLI->>Browser: open GUI URL with token fragment

    Browser->>GUIHost: request GUI assets
    GUIHost-->>Browser: serve React SPA
    Browser->>SPA: load application
    SPA->>SPA: read token from URL fragment
    SPA->>SPA: store token in sessionStorage
    SPA->>API: POST /api/v1/session with x-fmu-settings-api

    API->>API: verify bootstrap token
    API->>UserFMU: ensure ~/.fmu exists and load user config
    API->>Session: create or renew session
    API->>ProjectFMU: find_nearest_fmu_directory() if present
    API->>ProjectFMU: try acquire project lock
    API-->>SPA: set HttpOnly session cookie

    SPA->>API: subsequent requests with cookie
    API->>Session: resolve Session or ProjectSession
    API->>ProjectFMU: read/write project config, mappings, cache, changelog
    API->>UserFMU: read/write user config and API keys
```
