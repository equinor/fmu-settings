# Getting started

To get started you need to initialize FMU Settings for your project.

## Initialize FMU Settings

### Initialization from the terminal - *Recommended!*

To initialize FMU Settings you must be in your FMU project root, meaning within a revision directory of your model. This directory should contain a subdirectory called `ert`.

Example of a how a standard project path could look like:
`project/asset/resmod/ff/25.0.0`

In this example the `25.0.0` folder is the revision folder and the FMU project root, and initialization should be run from within this revision folder. FMU Settings will verify that the project folder contains a subfolder named `ert` to identify your project as a FMU project.

1.	Go to the project root:
```bash
cd  project/asset/resmod/ff/25.0.0
```

2.	From here, run the command:
```bash
fmu init
```

You have now initialized FMU Settings.

   >##### Important:
   >**For early onboarders to SUMO**, that already have masterdata in the global config before initialization of FMU Settings: 
   >
   >The initialization triggers FMU Settings to look for an existing global config file at the standard location: `fmuconfig/output/global_variables.yml`. If a valid configuration is found here, FMU Settings will import the sections `masterdata`, `model` and `access`,  so that you will not have to configure everything again.
   >
   >**NB! Stratigraphy is not imported**. Stratigraphy data must be configured directly in the GUI. When configuration of the stratigraphy is completed in the FMU Settings GUI, these sections should be deleted from the global config yaml file.

3. Open FMU Settings:
```bash
fmu settings
```

### Initialization from the GUI
Initialization of a project can also be done from the FMU Settings GUI.

1. Start the FMU Settings application:
```bash
fmu settings
```

2. Open the project selector:
   - from the start page by clicking **Select project**
   - or from **Project > Overview** by clicking the project select/change button

3. Enter the project path in the text field.

4. If the project is not yet initialized, FMU Settings asks if you want to initialize it.

5. The same initialization rules apply here as when running `fmu init` in the terminal:
   - the project folder must contain a subfolder `ert`
   - valid global config is searched for in `fmuconfig/output/global_variables.yml`
   - valid global config is also searched for in files matching `global*.yml` under `fmuconfig/input/`
   - available `masterdata`, `model`, and `access` are imported automatically

6. Confirm, and the FMU Settings application will initialize and open the project.


## How to open FMU Settings when your project is already initialized

1. Go to the project root (revision folder):
```bash
cd project/asset/resmod/ff/25.0.0
```

2. Run:
```bash
fmu settings
```

NB: FMU Settings can be opened from anywhere in your project folder hierarchy by running the command `fmu settings`. FMU Settings will in that case automatically detect the nearest project. Inside the FMU Settings GUI you will be able to open a project either from the list of **recent projects** or by entering the project path manually. 

Once the FMU Settings project is open, continue with the [GUI user guide](gui_user_guide.md).
