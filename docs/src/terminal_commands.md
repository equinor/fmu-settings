# Terminal commands

The commands most users need are:

- `fmu settings`
- `fmu init`
- `fmu sync`
- `fmu copy`

## `fmu settings`

This is the normal way to open FMU Settings.

```bash
fmu settings
```

This opens the FMU Settings application in your browser.

If a project is already known, FMU Settings may open it automatically. If not, you can choose the project in the GUI.

## `fmu init`

Use this command to set up a project for FMU Settings.

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

## `fmu sync`

Use this command when you want to copy FMU Settings content from one revision to another.

```bash
fmu sync --from /path/to/source/revision --to /path/to/target/revision
```

FMU Settings will:

- compare the `.fmu/` content in the two revisions
- show you what is different
- ask for confirmation before anything is merged

This is useful when you have updated FMU Settings in one revision and want to bring those changes into another revision.

The `--to` path is required and is the revision you want to copy settings to.

The `--from` path defaults to the current directory, so you can omit it if you are already in the source revision.

## `fmu copy`

`fmu copy` is the replacement for the `fmu_copy_revision` script. Use it to copy a FMU revision folder to a new location.

```bash
fmu copy --source /path/to/source/revision --target /path/to/target/revision
```

Run it without arguments to use an interactive menu instead:

```bash
fmu copy
```

The command also copies the `.fmu/` folder, so FMU Settings content is carried over to the new revision automatically.

### Copy profiles

The default profile is **4**. Use `--profile` to choose a different one:

| Profile | What it does |
|---------|-------------|
| 1 | Copy everything |
| 2 | Skip `backup/`, `users/`, `attic/`, `.git`/`.svn`, and files ending with `~` |
| 3 | As profile 2, plus skip `ert/output`, `ert/*/storage`, `rms/input/seismic`, `rms/model/*.log`, `rms/output` files, `spotfire/` inputs and models, and `share/results` and `share/templates` |
| 4 | As profile 3, but also removes empty folders at the destination *(default)* |
| 5 | As profile 3, but keeps `rms/output`, `share/results`, and `share/templates` |
| 6 | Only copy the `share/coviz/` folder |
| 9 | Use a custom rsync filter file |

### Other options

- `--threads` — number of threads (defaults to max available)
- `--cleanup` — remove the target folder if it already exists before copying
- `--merge` — attempt an rsync merge if the target already exists (experimental; cannot be combined with `--cleanup`)
- `--dryrun` — preview what would be copied without writing anything
- `--skipestimate` / `--skip` — skip estimating the size of the source revision before copying
- `--all` — list all folders

## Typical use

Set up a project and open FMU Settings:

```bash
cd /path/to/project
fmu init
fmu settings
```

Open the application and choose the project there:

```bash
fmu settings
```

Copy FMU Settings content from one revision to another:

```bash
fmu sync --from /project/revision_a --to /project/revision_b
```

Copy a revision folder to a new location:

```bash
fmu copy --source /project/revision_a --target /project/revision_b
```
