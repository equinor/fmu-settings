# Getting started

To get started, initialize FMU Settings for your project. This creates the hidden `.fmu` folder used to store project settings.

## Initialize FMU Settings

Initialization is done in the terminal in your TGX session.

To initialize FMU Settings you must be in you FMU projects `root` folder, meaning in a folder that contains a subfolder called `ert`.

Example of a how a standard project path could look like:

`project/ff/resmod/25.0.0/ert/model`

In this example the `25.0.0` folder is the root folder, as it contains a subfolder called `ert`. This is how FMU Settings identifies your project as a FMU project.

1. Go to the project root:
   ```bash
   cd /path/to/project
   ```
2. From here, run the command:
   ```bash
   fmu init
   ```
The `fmu init` command will create a `.fmu` folder at this location in the project path. (Remember, it will be a hidden folder so it will not be listed by the command `ll` or `ls`).

**You have now initialized FMU Settings and created your `.fmu` folder.**

The initialization triggers FMU Settings to look for existing global config files in these locations:
- `fmuconfig/output/global_variables.yml`
- files matching `global*.yml` under `fmuconfig/input/`

If any valid configuration is found here, FMU Settings will import the available data, so that you will not have to configure everything again. This can include data in the global config sections:
- `masterdata`
- `model`
- `access`

**NB: Stratigraphy is not imported. Stratigraphy data has to be configured directly in the GUI.**

3. Open FMU Settings:
   ```bash
   fmu settings
   ```

## How to open FMU Settings from the project folder when you already have `.fmu` in place:
1. Go to the project root:
   ```bash
   cd /path/to/project
   ```
2. Run:
   ```bash
   fmu settings
   ```

Once the FMU Settings project is open, continue with the [GUI user guide](gui_user_guide.md).
