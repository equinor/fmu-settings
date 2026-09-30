# GUI user guide

This guide is built around the **project setup checklist** in FMU Settings.

For most users, the main goal is simple: open the project and work through the checklist until the setup is complete.

## Project setup checklist

On the home page, FMU Settings shows a checklist that helps you see what is missing to complete your project configuration.

The checklist tracks whether the project has:

- model information and access control
- masterdata
- RMS project, stratigraphy, and wellbores
- stratigraphy and wellbore mappings

This guide follows that same setup flow.

```{figure} _static/homepage.png
:alt: FMU Settings home page
:width: 900px
:align: center

The FMU Settings home page with the project setup checklist.
```

## Start the application

Start the GUI from the command line:

```bash
fmu settings
```

FMU Settings opens in your browser.

## Select a project

If no project is selected, the front page shows a **Select project** button.

In the project selector dialog you can:

- choose one of your recent projects
- enter a project path manually

If the project is already initialized (has a `.fmu` folder), it opens directly.

If the project has not been initialized yet, FMU Settings can do that for you and then open it. See [Getting started](getting_started.md) for more information about initializing a project.

## Home page

The home page gives you a quick overview of the project. It shows:

- the currently selected project
- when it was last modified
- a short model description, if one is set
- a project setup checklist

## Step 1: Fill in project information

The **Project** page is the main page for the selected project.

Here you can see:

- basic project information
- current lock status
- model information
- access control settings

You can also use **Change project** to open another project.

### Read-only and editable mode

To avoid people overwriting each other's work, the project can be either:

- **editable**
- **read-only**

If the project is read-only, try **Enable editing**. If someone else is already editing, FMU Settings shows who currently holds the lock.

### Model

The **Model** section contains information about the model:

- name
- revision
- description

Each model needs a _name_ and _revision_, usually matching your project's directory structure. For example, for the project path `/project/field/resmod/ff/25.0.0/`, the name would be _ff_ and the revision _25.0.0_.

### Access control

The **Access control** section is used for exported data.

This section is used to configure access permissions for data exported from the project.

Here you choose:

- the Sumo target asset
- the default classification

Supported classifications are:

- `internal`
- `restricted`

The _asset_ specifies the target asset in Sumo where data will be uploaded. The _classification_ sets the default information classification for the data.

Read more about access control in the <a href="https://fmu-docs.equinor.com/docs/sumo/documentation/access_control" target="_blank" rel="noopener noreferrer">Sumo documentation</a>.

Pick a Sumo asset from the list when possible. If you cannot find the asset there, you can type it in yourself.

## Step 2: Add the SMDA subscription key

Open the **API keys** page from the left menu under **User > API keys**.

This page is where you save personal API keys used by FMU Settings.

Right now, this page is used for the SMDA subscription key. You need this key when working with masterdata in the GUI.

The page itself includes instructions for how to get the SMDA subscription key, so you can follow the steps there when setting it up.

After you save the key, it is hidden in the application.

```{note}
[SMDA](https://smda.equinor.com) is the database containing the master data.
```

## Step 3: Set up masterdata

The **Masterdata** page shows the masterdata references saved in the project, including:

- field
- country
- coordinate system
- stratigraphic column
- discoveries

To update masterdata:

1. Make sure the project is editable.
2. Make sure an SMDA subscription key has been added on **User > API keys**.
3. Enable editing mode on the Masterdata page.
4. If FMU Settings says required data is missing, use the guidance shown on the page to log in with SSO or add the access token to the session.

When editing is enabled, you can add or update masterdata from SMDA.

If required data for editing masterdata is not present, the page tells you what is missing. In practice this means checking that:

- an SMDA **subscription key** is present
- an SSO **access token** is present

## Step 4: Set up RMS project data

The **RMS** pages connect the FMU project to its RMS project. Use these pages to select the stratigraphy and wellbores to use in mappings.

### Select RMS project

Open **RMS > Overview**. This page shows the main RMS project in the `rms/model` directory. FMU Settings detects the version automatically.

Use **Select RMS project** or **Change RMS project** to choose the RMS project.

### Access the RMS project

FMU Settings must access the selected RMS project before it can read the stratigraphy and wellbores.

To access the RMS project:

1. Open **RMS > Overview**.
2. Select **Access RMS project**.
3. Wait until the page shows that the RMS project is ready for access. This can take a while.

```{note}
FMU Settings accesses the RMS project in read-only mode.
```

Select **Reload RMS project** to refresh the RMS data. If you want to choose a different RMS project, first select **Close RMS access**. When you switch FMU projects, FMU Settings closes RMS access automatically.

### Set project stratigraphy

Open **RMS > Stratigraphy** to select the RMS horizons and zones to store in the project. This page does not create SMDA mappings.

The RMS project must be ready for access before FMU Settings can read the available stratigraphy.

To set the project stratigraphy:

1. Select **Add** or **Edit**.
2. Select horizons and zones to add or remove them. You can also use **Add all** or **Remove all**.
3. Select **Save**.

Only the stratigraphy stored in the project is available on the stratigraphy mappings page.

If the project contains horizons or zones that no longer exist in RMS, FMU Settings asks you to remove them before saving.

### Set project wellbores

Open **RMS > Wellbores** to select the RMS wellbores to store in the project.

The RMS project must be ready for access before FMU Settings can read the available wellbores.

To set the project wellbores:

1. Select **Add** or **Edit**.
2. Use the **Include** checkboxes to select wellbores. You can filter the list and use the buttons to select or deselect all filtered wellbores.
3. Select **Planned** to set a wellbore as a planned wellbore.
4. Select **Save**.

```{note}
Planned wellbores can be mapped to simulator names, but not to SMDA names. They appear as blue rows on the wellbore mappings page.
```

## Step 5: Map RMS stratigraphy to the stratigraphic column in SMDA

Open **Mappings > Stratigraphy** to map the stored RMS stratigraphy to the SMDA stratigraphic column selected in **Masterdata**.

The page displays the stratigraphy selected in **Step 4**, with the source names marked as "RMS". Each horizon and zone has a corresponding SMDA field. The field shows `(not set)` until it is mapped.

This page is separate from **RMS > Stratigraphy**. The RMS page controls which horizons and zones are stored. The mappings page controls the SMDA name and RMS aliases for each stored element.

In SMDA, zones are stratigraphic units. Horizons define the tops and bases of those units.

### Map RMS to the stratigraphic column in SMDA

1. Make sure that the project is editable, and then enable editing mode.
2. Select the Edit icon (pen symbol) for the zone or horizon to map.
3. Select the corresponding SMDA name from the selected stratigraphic column.
4. If needed, add one or more aliases for the RMS name.
5. Select **Save**.

Map zones first. After you map an adjacent zone, its top and base horizons appear at the top of the list of available SMDA options for the RMS horizon.

If an RMS zone or horizon is not defined in the SMDA stratigraphic column, select **Zone doesn't exist in SMDA** or **Horizon doesn't exist in SMDA**.

## Step 6: Map RMS wellbores

Open **Mappings > Wellbores** to manage RMS, simulator, and SMDA names for the wellbores selected in **Step 4**.

Make sure that the project is editable, and then enable editing mode. To map SMDA names, you must also have:

- a field in the project masterdata
- an SMDA subscription key
- an active SSO access token

### Edit one wellbore

To edit one wellbore:

1. Select its row in the table.
2. Enter its **Simulator name**, select its **SMDA name**, or do both.
3. Select **Save**.

If the wellbore is not defined in SMDA, select **Wellbore doesn't exist in SMDA**. This completes the SMDA mapping task for that wellbore.

Planned wellbores can only have simulator names.

### Import or export simulator names

If no simulator names are saved, select **Import simulator names** to read them from an `rms_eclipse.csv` file. The default path is:

```text
rms/input/well_modelling/well_info/rms_eclipse.csv
```

FMU Settings reads the `RMS_WELL_NAME` and `ECLIPSE_WELL_NAME` columns. It imports names only for RMS wellbores that are stored in the project.

When simulator names are saved, select **Export simulator names** to write an RMS simulator renaming table. The default path is:

```text
rms/input/well_modelling/well_info/rms_simulator.renaming_table
```

You can enter another path relative to the project root for either operation. FMU Settings asks for confirmation before it overwrites an existing renaming table.

### Get suggested SMDA names

Projects can contain thousands of wellbores. Mapping each RMS name to an SMDA name manually can take a long time. **Suggest SMDA names** compares the names and proposes likely matches for non-planned RMS wellbores that are not yet mapped.

Identical names most likely refer to the same wellbore. However, RMS and SMDA can use different prefixes for that wellbore. For example, one system can include a country prefix while the other does not. Ignoring the prefix lets FMU Settings compare the remaining parts of the names.

To generate suggestions:

1. Select **Suggest SMDA names**.
2. In **Prefixes to ignore**, keep or change the prefixes used for name comparison. Country prefixes are selected by default. You can also add other prefixes.
3. Select **Generate suggestions**.
4. Review each suggested RMS and SMDA pair. Select only the pairs that refer to the same wellbore.
5. Select **Save selected SMDA names**.

Prefix rules change only the comparison. FMU Settings saves the complete SMDA name. Exact name matches are selected automatically.

```{warning}
Suggested matches are based on name similarity. A matching name does not prove that the RMS and SMDA names refer to the same wellbore. Verify each suggestion before saving it.
```

To complete the project setup checklist, each non-planned RMS wellbore must have an SMDA name or the **Wellbore doesn't exist in SMDA** selection.

## Optional: Review earlier saved versions

The **History** page lets you look at earlier saved versions of project data.

You can currently browse saved versions of:

- project configuration
- mappings

Choose a resource to view its snapshots, listed from newest to oldest.

For each saved version, you can:

- use **View details**
- compare it with what you have now
- restore it

Use **View details** to see what has changed between the snapshot and the current version. If the project is editable, you can also restore from the snapshot.

When you restore an earlier version, FMU Settings first saves a backup of the current one.

You cannot restore while the project is read-only.

### Set the maximum number of snapshots

Use **Max snapshots** to control how many snapshots FMU Settings keeps on disk for the project.

1. Select the maximum number of snapshots to keep.
2. Select **Save**.

If you reduce the maximum, FMU Settings shows how many old snapshots will be deleted before you confirm the change. You cannot change this setting while the project is read-only.

## Optional: Recover deleted user files

Open **User > Recovery** to recover files that were deleted from your user `.fmu` directory while FMU Settings was running.

1. Select **Check for deleted files**.
2. Review the files that can be recovered.
3. Select **Recover**.

Files that were not deleted are not affected. FMU Settings cannot recover files that were deleted before the application started.

## Summary

For a new project, a simple order is:

1. Open or initialize the project.
2. Fill in **Project** information.
3. Add the SMDA subscription key on **User > API keys**.
4. Set and verify **Masterdata**.
5. Set the **RMS** project.
6. Select the RMS stratigraphy and wellbores to store in the project.
7. Map the stored RMS stratigraphy to the selected SMDA stratigraphic column.
8. Map non-planned RMS wellbores to SMDA names. Add simulator names if the project needs them.

If you need to look back at earlier saved versions, use the **History** page.
