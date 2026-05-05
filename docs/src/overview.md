# Overview

## What is FMU Settings?

FMU Settings is a web application (localhost) that provides a user-friendly solution with a GUI for static configuration in FMU projects. FMU Settings offers a unified way to connect FMU projects to other data sources within the company, i.e. SMDA. 

## Why FMU Settings?

Today, configuring your FMU project and connecting the data produced by FMU to the official masterdata in SMDA, is done by manually editing the global configuration yaml file. This can be a tedious and error-prone process. 

Especially the mapping of stratigraphic data to official data in SMDA has a high risk of typos, and quality checking and validation is difficult.
Example: A zone called `Upper Tarbert 2.3` in RMS can be equal to a grid zone called `UT2-3` in the simulator, and the corresponding unit in SMDA could be `Tarbert Upper Fm.`. When moving data to cloud (SUMO) these must be connected and identified as the same zone/unit. 

This process that requires editing yaml files and manually adding master data from official databases does not scale when the amount of data that needs to be mapped increases. FMU Settings is made to address these concerns by offering a simple user interface to configure your FMU project and connect FMU data to the official databases, including validation of the data.

The need for mapping of FMU data from RMS and simulators to official databases is not limited to stratigraphy, it will also include wells, production data etc.

**FMU Settings can:**

•	Extract stratigraphy from the RMS project

•	Connect to SMDA data directly through the GUI

•	Provide a best-attempt automatic mapping to match RMS names to SMDA names

•	Allow user to QC and validate mapping against SMDA and project files

By using FMU Settings you get benefits like a **web-based GUI**, **simplified configuration** of FMU projects and a **stronger data quality** guarantee.

#### What you can do in FMU Settings vs how it is done without FMU Settings

| Task | How it is done today | How it will be done in FMU Settings |
| ----- | ---------------------- | ---------------------------------------- |
| Start using SUMO | Manually add masterdata and metadata to global config yaml file. | Run a terminal command to initialize a FMU Settings project. Configuration of masterdata and metadata is then done through the FMU Settings GUI.
| Add model masterdata | Open SMDA, find field and copy masterdata (on FMU format), manually paste masterdata into yaml file. Prone to errors. | GUI is connected to SMDA, masterdata is fetched and validated in the GUI, and stored to FMU project.
| Add model stratigraphy | Manually add and update stratigraphic column (horizons and zones) in yaml file, based on stratigraphic column in SMDA. Highly prone to errors. | GUI is connected to SMDA and RMS, stratigraphy in RMS and stratigraphic column in SMDA can be mapped in the GUI, creating a consistent stratigraphic column between several data sources.
| Track changes in global config | No version control of global config, all changes are done manually and anyone with access to project area can edit the yaml file. | Tracking of version history and functionality for restoring earlier versions if needed. |

## How does FMU Settings work?

By initializing FMU Settings for your FMU project a folder called `.fmu` is automatically created in your project’s root folder.
This `.fmu` folder is used to store all your project settings and project metadata. FMU Settings allows you to work with the content in the `.fmu` folder in a GUI, instead of having to edit configuration files manually.

**NB! You should not edit anything inside the `.fmu` folder manually. All configuration and changes should be done through the FMU Settings GUI!**


From here, continue with [Getting started](getting_started.md).
