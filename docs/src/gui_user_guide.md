# GUI user guide

This guide is built around the **project setup checklist** in FMU Settings.

For most users, the main goal is simple: open the project and work through the checklist until the setup is complete.

## Project setup checklist

On the home page, FMU Settings shows a checklist that helps you see what is still missing.

The checklist tracks whether the project has:

- model information and access control
- masterdata
- RMS project and stratigraphy
- stratigraphy mappings

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

If the project already has a `.fmu/` folder, it opens directly.

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

The **Model** section contains information about the model.

- name
- revision
- description

Each model needs a *name* and *revision*, usually matching your project's directory structure. For example, for the project path `/project/field/resmod/ff/25.0.0/`, the name would be *ff* and the revision *25.0.0*.

### Access control

The **Access control** section is used for exported data.

This section is used to configure access permissions for data exported from the project.

Here you choose:

- the Sumo target asset
- the default classification

Supported classifications are:

- `internal`
- `restricted`

The *asset* specifies the target asset in Sumo where data will be uploaded. The *classification* sets the default information classification for the data.

Pick a Sumo asset from the list when possible. If you cannot find the asset there, you can type it in yourself.

## Step 2: Add the SMDA subscription key

Open the **API keys** page from the left menu under **User > API keys**.

This page is where you save personal API keys used by FMU Settings.

Right now, this page is used for the SMDA subscription key. You need this key when working with masterdata in the GUI.

The page itself includes instructions for how to get the SMDA subscription key, so you can follow the steps there when setting it up.

After you save the key, it is hidden in the application.

## Step 3: Set up masterdata

The **Masterdata** page shows the masterdata saved in the project, including:

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

## Step 4: Set up RMS project and stratigraphy

The **RMS** page is where you connect the FMU project to its RMS project and choose the project stratigraphy that can later be mapped to SMDA stratigraphic columns.

### Select RMS project

The page shows the main RMS project located in the `rms/model` directory. The version is detected automatically.

Use **Select RMS project** or **Change RMS project** to choose the correct one.

### Set project stratigraphy

The RMS project must be open before FMU Settings can access data such as zones and horizons.

Once the RMS project is open, you can update the project stratigraphy.

The stratigraphy editor shows:

- the current project stratigraphy
- the available RMS stratigraphy

You can click horizons and zones to add or remove them. There are also **Add all** and **Remove all** buttons.

If the project contains horizons or zones that no longer exist in RMS, FMU Settings asks you to remove them before saving.

## Step 5: Map RMS stratigraphy to SMDA

<!-- TODO: Add content for the Mappings page -->

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

## Summary

For a new project, a simple order is:

1. Open or initialize the project.
2. Fill in **Project** information.
3. Add the SMDA subscription key on **User > API keys**.
4. Set and verify **Masterdata**.
5. Set the **RMS** project and import the relevant stratigraphy.
6. Map the RMS stratigraphy to SMDA stratigraphic columns on the **Mappings** page.

If you need to look back at earlier saved versions, use the **History** page.
