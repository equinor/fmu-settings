# Overview

## What is FMU Settings?

FMU Settings is a web application (localhost) that provides a user-friendly solution with a GUI for static configuration in FMU projects. FMU Settings offers a unified way to connect FMU projects to other data sources within the company, i.e. SMDA. 

## Why FMU Settings?

For FMU results to be usable by other applications, they need to be referenced to master data - unique and shared definitions. Configuring these references by manually editing config files can be a tedious and error-prone process. Especially the mapping of stratigraphic data to definitions in the official stratigraphic column has a high risk of typos, and quality checking and validation is difficult.

Example: A zone called `UpperTarbert23` in RMS can be equal to a grid zone called `UT2-3` in the simulator, and the corresponding unit in SMDA could be `Tarbert Upper Fm.`. When storing data to cloud (Sumo) these must be connected and identified as the same zone/unit.

FMU Settings is made to address these concerns by offering a simple user interface to configure your FMU project and connect FMU data to the official databases, including validation of the data.

The need for referencing master data is not limited to stratigraphy. It will also include wells, production data etc.

**FMU Settings can:**

•	Extract stratigraphy from the RMS project

•	Connect to SMDA data directly through the GUI

•	Provide a best-attempt automatic mapping to match RMS names to SMDA names

•	Allow user to QC and validate mapping against SMDA and project files

By using FMU Settings you get benefits like a **web-based GUI**, **simplified configuration** of FMU projects and a **stronger data quality** guarantee.

#### What you can do in FMU Settings vs how it is done without FMU Settings

| Task | How it is done today | How it will be done in FMU Settings |
| ----- | ---------------------- | ---------------------------------------- |
| Start using Sumo | Manually add masterdata and metadata to global config yaml file. | Run a terminal command to initialize a FMU Settings project. Configuration of masterdata and metadata is then done through the FMU Settings GUI.
| Add model masterdata | Open SMDA, find field and copy masterdata (on FMU format), manually paste masterdata into yaml file. Prone to errors. | GUI is connected to SMDA, masterdata is fetched and validated in the GUI, and stored to FMU project.
| Add model stratigraphy | Manually add and update stratigraphic column (horizons and zones) in yaml file, based on stratigraphic column in SMDA. Highly prone to errors. | GUI is connected to SMDA and RMS, stratigraphy in RMS and stratigraphic column in SMDA can be mapped in the GUI, creating a consistent stratigraphic column between several data sources.
| Track changes in global config | No version control of global config, all changes are done manually and anyone with access to project area can edit the yaml file. | Tracking of version history and functionality for restoring earlier versions if needed. |

## How does FMU Settings work?

By initializing FMU Settings for your FMU project a folder called `.fmu` is automatically created in your project’s root folder.
This `.fmu` folder is used to store all your project settings and project metadata. FMU Settings allows you to work with the content in the `.fmu` folder in a GUI, instead of having to edit configuration files manually.

**NB! You should not edit anything inside the `.fmu` folder manually. All configuration and changes should be done through the FMU Settings GUI!**



From here, continue with [Getting started](getting_started.md).

--------------

```{note}
*Aspen RMS™ is a registered trademark of Aspen Technology, Inc. (AspenTech). Use of RMS™ is governed by AspenTech's licensing terms and conditions. It is proprietary software and is neither open-source nor free. A valid license agreement with AspenTech is required for its use.*

*FMU Settings is an independent project developed by Equinor and is neither produced by nor affiliated with AspenTech. It is open-source and free software released under the GPL v3 license.*
```