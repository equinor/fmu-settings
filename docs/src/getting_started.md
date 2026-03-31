# Getting started

This page covers two different situations:

1. You are setting up FMU Settings for a project that does not yet have a `.fmu/` folder.
2. You already have a `.fmu/` folder and just want to open the project.

## If the project does not yet have `.fmu/`

For a new project, we recommend initializing it from the terminal first.

### Recommended: initialize from the terminal

To initialize the project, FMU Settings expects a valid FMU project root. At the moment, that means the project folder must contain a subfolder `ert`.

For example, this would be a valid project root:

`/path/to/my_project`

if it contains:

`/path/to/my_project/ert`

1. Go to the project root:

   ```bash
   cd /path/to/project
   ```

2. Run:

   ```bash
   fmu init
   ```

`fmu init` creates a `.fmu/` folder in the project path.

When a project is initialized, FMU Settings looks for existing global FMU configuration in these locations:

- `fmuconfig/output/global_variables.yml`
- files matching `global*.yml` under `fmuconfig/input/`

If valid configuration is found, FMU Settings imports the available data into the project config. This can include:

- `masterdata`
- `model`
- `access`

Stratigraphy is not imported by `fmu init`. You can continue that setup later in the GUI.

3. Open FMU Settings:

   ```bash
   fmu settings
   ```

### You can also initialize from the GUI

If you prefer, you can initialize the project from FMU Settings itself.

1. Start the application:

   ```bash
   fmu settings
   ```

2. Open the project selector:
   - from the start page by clicking **Select project**
   - or from **Project > Overview** by clicking the project select/change button

3. Enter the project path in the text field.
4. If the project does not yet have a `.fmu/` folder, FMU Settings asks whether you want to initialize it.
5. The same initialization rules apply here as when running `fmu init` in the terminal:
   - the project folder must contain a subfolder `ert`
   - valid global config is searched for in `fmuconfig/output/global_variables.yml`
   - valid global config is also searched for in files matching `global*.yml` under `fmuconfig/input/`
   - available `masterdata`, `model`, and `access` are imported automatically

6. Confirm, and the application will create `.fmu/` and open the project.

## If the project already has `.fmu/`

If the project is already initialized, you can open it in either of these ways.

### Open it directly from the project folder

1. Go to the project path:

   ```bash
   cd /path/to/project
   ```

2. Run:

   ```bash
   fmu settings
   ```

If you start FMU Settings from the project path, it will automatically open that project.

### Open it from anywhere

You can also start FMU Settings from any location:

```bash
fmu settings
```

Then open the project by:

- choosing it from **recent projects**
- or entering the project path manually

## Next step

Once the project is open, continue with the [GUI user guide](gui_user_guide.md).
