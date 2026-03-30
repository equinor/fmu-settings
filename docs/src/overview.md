# Overview

FMU Settings creates and manages the `.fmu/` folder in an FMU project.

This folder is used to store project settings and metadata, and FMU Settings gives you a GUI for working with that content instead of editing configuration files manually.

## What `.fmu/` is

`.fmu/` is a hidden folder inside an FMU project.

It is where FMU Settings stores project-specific settings and related data, so the project keeps its own configuration close to the project itself.

Inside `.fmu/`, FMU Settings stores information such as:

- project configuration
- mappings
- version history of changes

The project configuration contains settings such as model information, access settings, masterdata, and RMS-related information.

Mappings means saved links between project-specific names or identifiers and official references. One example is mapping RMS stratigraphic framework to the SMDA stratigraphic column. In future development, this can also include mapping RMS and simulator well names to SMDA well names.

You normally do not need to edit anything inside `.fmu/` manually. FMU Settings is meant to manage that for you.

## Why use this instead of editing global config YAML manually?

Editing global config YAML files manually can work, but it also has some downsides:

- it is easy to make typing, formatting, or structure mistakes
- it can be hard to know exactly what should be changed
- changes can become harder to track over time

FMU Settings improves this by giving you:

- a GUI for editing settings instead of changing YAML by hand
- validation of the data being saved
- version history so earlier states can be inspected or restored
- protection against conflicting edits when multiple users work on the same project

The global config can still be a useful source of existing information during initialization, but FMU Settings is meant to be the easier place to maintain project settings afterwards.

## What you can do in FMU Settings

FMU Settings helps you:

- initialize a project and create `.fmu/`
- work with project metadata and masterdata through the GUI
- map RMS stratigraphic framework to the SMDA stratigraphic column
- inspect version history and restore earlier versions if needed

From here, continue with [Getting started](getting_started.md).
