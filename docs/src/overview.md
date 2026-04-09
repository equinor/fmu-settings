# Overview

To be able to use FMU Settings you need to have a folder called `.fmu` in your FMU project. 

The `.fmu` folder is used to store all your project settings and project metadata, and FMU Settings allows you to  work with the content in the `.fmu` folder in a GUI , instead of having to edit configuration files manually.

FMU Settings consists of  the `.fmu` folder + the FMU Settings GUI. This is replacing the global config files that had to be created and updated manually, thus being highly prone to errors and difficult to keep synchronized. FMU Settings improves this by allowing you to handle all these project configurations in a GUI. It also offers data validation and version history.


## What is `.fmu`?

`.fmu` is a hidden folder inside a FMU project (the `.` before a folder name means it is a hidden folder).
Inside the `.fmu` folder, FMU Settings stores information such as:
- Project configuration
    - Model information, access settings, masterdata, and RMS-related information.
- Mappings
    - Saved links between project-specific names or identifiers and official references. One example is mapping RMS stratigraphic framework to the SMDA stratigraphic column.
- Version history and change log


**NB! You should not edit anything inside the `.fmu` folder manually. All configuration and changes should be done through the FMU Settings GUI!**


## What you can do in FMU Settings

- Run terminal commands to initialize a FMU Settings project and create the `.fmu` folder
- Configure FMU project metadata and masterdata through the FMU Settings GUI
- Map RMS stratigraphic framework to the SMDA stratigraphic column
- Inspect version history and restore earlier versions if needed


From here, continue with [Getting started](getting_started.md).
