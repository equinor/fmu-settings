# FMU Settings documentation

**FMU Settings** is a tool developed for simplifying adding metadata when 
exporting data from FMU workflows. It simplifies the process of adding metadata 
from official sources like SMDA and replaces the need for having metadata defined 
in the global configuration file. 

Main features of FMU Settings:
- GUI for configuration of project FMU metadata
- Connection to SMDA and official metadata
- GUI for mapping RMS stratigraphy to SMDA stratigraphic column
- Version control

If you are new to FMU Settings, it is recommended to start with:

- Getting an [Overview](overview.md) of what it is and how it is used
- Then, [Get Started](getting_started.md) with the initialization and opening the FMU Settings GUI
- Follow the [GUI userguide](gui_userguide.md) to configure everything and set up metadata for your project

If you find bugs, need help, or want to talk to the developers, reach out via:

- [GitHub Issues](https://github.com/equinor/fmu-settings/issues)
- The [FMU portal](https://fmu.equinor.com)

Future developments:
- Mapping of well names (RMS - Simulator - SMDA)
- Handling of and syncronization between user copies and master project
- 



```{toctree}
:maxdepth: 2
:hidden:

overview.md
getting_started.md
gui_userguide.md
cli_commands.md

```