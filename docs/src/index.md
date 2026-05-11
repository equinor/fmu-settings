# FMU Settings documentation

**FMU Settings** is a tool that will simplify the handling of FMU model metadata, meaning metadata related to the FMU model itself and metadata needed when you are exporting data objects from FMU models.

FMU Settings lets you manage static configuration through a graphical user interface (GUI) instead of editing files manually. In FMU Settings GUI, you can:
- Set up FMU project metadata
- Link FMU models to SMDA and other official metadata sources, including 
    - mapping of RMS stratigraphy to the SMDA stratigraphic column
    - *mapping of wells between RMS, Eclipse and SMDA (future feature, currently not implemented)*
- keeping track of version history for your FMU project settings

### If you are new to FMU Settings
1. Read the [Overview](overview.md) page to learn what FMU Settings is and how it is used.
2. Follow instructions on the [Getting started](getting_started.md) page to get started with FMU Settings for your FMU model(s).
3. Use the [GUI user guide](gui_user_guide.md) to configure and add metadata to your FMU model(s).
4. See also [Terminal commands](terminal_commands.md) for the most common terminal commands relevant for FMU Settings.

### Feedback
If you find bugs, need help or have questions or if you have suggestions for new features, use:
- <a href="https://equinor.enterprise.slack.com/archives/C09MFKN4NC9" target="_blank" rel="noopener noreferrer">#fmu-settings slack channel</a>
- <a href="https://fmu.equinor.com" target="_blank" rel="noopener noreferrer">FMU portal</a>

### Upcoming features

FMU Settings is still being developed and some of the coming features will be:
- mapping of well names between RMS, Eclipse/Flow (or other simulators) and SMDA (or other sources)
- handling of and synchronization between user copies and the master project


```{toctree}
:maxdepth: 2
:hidden:

overview.md
getting_started.md
gui_user_guide.md
terminal_commands.md
data_models.md

```
