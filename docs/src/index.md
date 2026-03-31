# FMU Settings documentation

**FMU Settings** is a tool for making it easier to add metadata when exporting data from FMU workflows.

It helps you add metadata from official sources such as SMDA and reduces the need to keep the metadata in the global configuration file.

FMU Settings provides a GUI where you can:

- set up FMU project metadata
- work with SMDA and other official metadata sources
- map RMS stratigraphy to the SMDA stratigraphic column
- view version history for project settings

If you are new to FMU Settings, a good place to start is:

- Read the [Overview](overview.md) to see what FMU Settings is and how it is used.
- Follow [Getting started](getting_started.md) to initialize a project or open a project that already has `.fmu/`.
- Use the [GUI user guide](gui_user_guide.md) to continue setting up metadata in the application.
- See [Terminal commands](terminal_commands.md) for the most common terminal commands.
- See [Data models](data_models.md) if you want to inspect the schemas used by FMU Settings.

If you find bugs, need help, or want to get in touch, use:

- <a href="https://equinor.enterprise.slack.com/archives/C09MFKN4NC9" target="_blank" rel="noopener noreferrer">#fmu-settings slack channel</a>
- [Atlas team email](mailto:fg_fmu-atlas@equinor.com)
- <a href="https://github.com/equinor/fmu-settings/issues" target="_blank" rel="noopener noreferrer">GitHub issues</a>
- <a href="https://fmu.equinor.com" target="_blank" rel="noopener noreferrer">FMU portal</a>

Future developments:

- mapping of well names between RMS, simulator, and SMDA
- handling and synchronization between user copies and the master project

```{toctree}
:maxdepth: 2
:hidden:

overview.md
getting_started.md
gui_user_guide.md
terminal_commands.md
data_models.md

```
